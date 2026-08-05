import datetime
import itertools
import re
from dataclasses import dataclass

from sqlalchemy import and_, not_, or_, select, text
from sqlalchemy.sql import ColumnElement

from app.db.models import (
    Article,
    Folder,
    Source,
    Subscription,
    UserArticleState,
)

_TOKEN_RE = re.compile(r'\(|\)|"[^"]*"|/[^/]*/|[^\s()]+')

_VALID_SEARCH_FIELDS = (
    "f",
    "c",
    "author",
    "intitle",
    "intext",
    "inurl",
    "date",
    "pubdate",
    "mdate",
    "userdate",
)


class SearchSyntaxError(Exception):
    pass


@dataclass
class _Token:
    kind: str
    value: str


def _tokenize(query: str) -> list[_Token]:
    tokens: list[_Token] = []
    for raw in _TOKEN_RE.findall(query):
        if raw == "(":
            tokens.append(_Token("LPAREN", raw))
        elif raw == ")":
            tokens.append(_Token("RPAREN", raw))
        elif raw.upper() == "AND":
            tokens.append(_Token("AND", raw))
        elif raw.upper() == "OR":
            tokens.append(_Token("OR", raw))
        elif raw.upper() == "NOT":
            tokens.append(_Token("NOT", raw))
        else:
            tokens.append(_Token("TERM", raw))
    return tokens


_param_counter = itertools.count()


def _fts_ids(match_expr: str) -> ColumnElement:
    param_name = f"fts_query_{next(_param_counter)}"
    subquery = text(
        f"SELECT rowid FROM articles_fts WHERE articles_fts MATCH :{param_name}"
    ).bindparams(**{param_name: match_expr})
    return Article.id.in_(subquery)


def _regexp_condition(pattern: str) -> ColumnElement:
    return Article.title.op("REGEXP")(pattern) | Article.content.op("REGEXP")(pattern)


def _parse_date_boundary(value: str, *, is_end: bool) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(value)
    has_time = "T" in value or " " in value.strip()
    if is_end and not has_time:
        parsed = parsed + datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)
    return parsed


def _date_condition(column, value: str) -> ColumnElement:
    if ".." in value:
        start_str, end_str = value.split("..", 1)
        conditions = []
        if start_str:
            conditions.append(column >= _parse_date_boundary(start_str, is_end=False))
        if end_str:
            conditions.append(column <= _parse_date_boundary(end_str, is_end=True))
        return and_(*conditions) if conditions else text("1=1")
    day = datetime.datetime.fromisoformat(value)
    next_day = day + datetime.timedelta(days=1)
    return and_(column >= day, column < next_day)


def _feed_condition(user_id: int, value: str) -> ColumnElement:
    subquery = (
        select(Subscription.source_id)
        .join(Source, Source.id == Subscription.source_id)
        .where(
            Subscription.user_id == user_id,
            (Subscription.custom_name.ilike(f"%{value}%")) | (Source.url.ilike(f"%{value}%")),
        )
    )
    return Article.source_id.in_(subquery)


def _category_condition(user_id: int, value: str) -> ColumnElement:
    subquery = (
        select(Subscription.source_id)
        .join(Folder, Folder.id == Subscription.folder_id)
        .where(Folder.user_id == user_id, Folder.name.ilike(f"%{value}%"))
    )
    return Article.source_id.in_(subquery)


def _userdate_condition(value: str) -> ColumnElement:
    subquery = select(UserArticleState.article_id).where(
        _date_condition(UserArticleState.read_at, value)
    )
    return Article.id.in_(subquery)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _fts_escape(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


class _Parser:
    def __init__(self, tokens: list[_Token], user_id: int) -> None:
        self.tokens = tokens
        self.pos = 0
        self.user_id = user_id

    def _peek(self) -> _Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self) -> _Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self) -> ColumnElement | None:
        if not self.tokens:
            return None
        return self._or_expr()

    def _or_expr(self) -> ColumnElement:
        left = self._and_expr()
        while self._peek() and self._peek().kind == "OR":
            self._advance()
            right = self._and_expr()
            left = or_(left, right)
        return left

    def _and_expr(self) -> ColumnElement:
        left = self._not_expr()
        while True:
            peek = self._peek()
            if not peek:
                break
            if peek.kind == "AND":
                self._advance()
                right = self._not_expr()
                left = and_(left, right)
                continue
            if peek.kind in ("TERM", "LPAREN", "NOT"):
                right = self._not_expr()
                left = and_(left, right)
                continue
            break
        return left

    def _not_expr(self) -> ColumnElement:
        peek = self._peek()
        if peek and peek.kind == "NOT":
            self._advance()
            return not_(self._atom())
        if peek and peek.kind == "TERM" and peek.value.startswith("-") and len(peek.value) > 1:
            token = self._advance()
            inner = self._term_to_expr(token.value[1:])
            return not_(inner)
        return self._atom()

    def _atom(self) -> ColumnElement:
        token = self._peek()
        if token is None:
            raise SearchSyntaxError("unexpected end of query")
        if token.kind == "LPAREN":
            self._advance()
            expr = self._or_expr()
            if not self._peek() or self._peek().kind != "RPAREN":
                raise SearchSyntaxError("missing closing parenthesis")
            self._advance()
            return expr
        if token.kind == "TERM":
            self._advance()
            return self._term_to_expr(token.value)
        raise SearchSyntaxError(f"unexpected token: {token.value}")

    def _term_to_expr(self, raw: str) -> ColumnElement:
        if raw.startswith("/") and raw.endswith("/") and len(raw) >= 2:
            return _regexp_condition(raw[1:-1])

        if ":" in raw:
            field, _, value = raw.partition(":")
            field_lower = field.lower()
            if field_lower in _VALID_SEARCH_FIELDS:
                value = _strip_quotes(value)
                if field_lower == "f":
                    return _feed_condition(self.user_id, value)
                if field_lower == "c":
                    return _category_condition(self.user_id, value)
                if field_lower == "author":
                    return Article.author.ilike(f"%{value}%")
                if field_lower == "intitle":
                    return _fts_ids(f"title:{_fts_escape(value)}")
                if field_lower == "intext":
                    return _fts_ids(f"content:{_fts_escape(value)}")
                if field_lower == "inurl":
                    return Article.url.ilike(f"%{value}%")
                if field_lower in ("date", "pubdate"):
                    return _date_condition(Article.published_at, value)
                if field_lower == "mdate":
                    return _date_condition(Article.fetched_at, value)
                if field_lower == "userdate":
                    return _userdate_condition(value)

        term = _strip_quotes(raw)
        return _fts_ids(_fts_escape(term))


def try_build_ranked_fts_query(query: str) -> str | None:
    tokens = _tokenize(query)
    if not tokens:
        return None
    parts: list[str] = []
    for token in tokens:
        if token.kind in ("LPAREN", "RPAREN"):
            parts.append(token.value)
        elif token.kind in ("AND", "OR"):
            parts.append(token.kind)
        elif token.kind == "NOT":
            parts.append("NOT")
        elif token.kind == "TERM":
            value = token.value
            if ":" in value and value.split(":", 1)[0].lower() in _VALID_SEARCH_FIELDS:
                return None
            if value.startswith("/") and value.endswith("/") and len(value) >= 2:
                return None
            if value.startswith("-") and len(value) > 1:
                parts.append("NOT")
                value = value[1:]
            parts.append(_fts_escape(_strip_quotes(value)))
        else:
            return None
    return " ".join(parts)


def parse_search_query(query: str, user_id: int) -> ColumnElement | None:
    tokens = _tokenize(query)
    parser = _Parser(tokens, user_id)
    return parser.parse()
