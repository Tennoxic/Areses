
export function Input({ className = "", ...props }) {
  return <input className={`ui-input ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }) {
  return (
    <div className="ui-select-wrapper">
      <select className={`ui-select ${className}`} {...props}>
        {children}
      </select>
      <span className="ui-select-caret" aria-hidden="true">▾</span>
    </div>
  );
}

export function Checkbox({ checked, onChange, children, id, className = "" }) {
  return (
    <label className={`ui-checkbox-label ${className}`} htmlFor={id}>
      <span className={`ui-checkbox-box ${checked ? "checked" : ""}`} aria-hidden="true">
        {checked && <span className="ui-checkbox-tick">✓</span>}
      </span>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="ui-checkbox-native"
      />
      {children && <span className="ui-checkbox-text">{children}</span>}
    </label>
  );
}

export function Slider({ value, min, max, step, onChange, unit = "", className = "" }) {
  const pct = max === min ? 0 : ((value - min) / (max - min)) * 100;
  return (
    <div className={`ui-slider-row ${className}`}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={onChange}
        className="ui-slider"
        style={{ "--pct": `${pct.toFixed(1)}%` }}
      />
      <span className="ui-slider-value">{value}{unit}</span>
    </div>
  );
}

export function Textarea({ className = "", ...props }) {
  return <textarea className={`ui-textarea ${className}`} {...props} />;
}
