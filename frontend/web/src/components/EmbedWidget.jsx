export default function EmbedWidget() {
  return (
    <div className="card">
      <h3>Embeddable Widget</h3>
      <p className="muted">
        Partners can embed a minimal “type → choose voice → hear” widget.
        Package the JS client and expose a custom element.
      </p>
      <code>
        &lt;script src="https://cdn.partner/dubfinity.js"&gt;&lt;/script&gt;
      </code>
    </div>
  );
}
