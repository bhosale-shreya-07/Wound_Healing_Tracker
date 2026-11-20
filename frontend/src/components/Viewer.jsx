import { useRef, useState } from "react";
import { api, fileUrl } from "../api";

export default function Viewer({ item, onChanged }) {
  const [drawing, setDrawing] = useState(false);
  const [poly, setPoly] = useState([]);
  const [err, setErr] = useState("");
  const ref = useRef();

  const add = (e) => {
    if (!drawing) return;
    const im = ref.current, r = im.getBoundingClientRect();
    setPoly([...poly, [((e.clientX - r.left) / r.width) * im.naturalWidth,
                       ((e.clientY - r.top) / r.height) * im.naturalHeight]]);
  };
  const save = async () => {
    try {
      await api(`/api/images/${item.id}/correct`, { method: "POST", body: { polygon: poly } });
      setDrawing(false); setPoly([]); setErr(""); onChanged();
    } catch (e) { setErr(e.message); }
  };
  const [aU, pU, a, p] = item.calibrated
    ? ["cm²", "cm", item.area_cm2, item.perimeter_cm]
    : ["px²", "px", item.area_px, item.perimeter_px];
  const c = item.comparison;

  return (
    <div className="panel">
      <h3>{item.captured_on}{item.manually_corrected && <span className="muted"> (boundary corrected by hand)</span>}</h3>
      <div className="metrics">
        <span>Area <b>{a?.toFixed(2)} {aU}</b></span>
        <span>Perimeter <b>{p?.toFixed(2)} {pU}</b></span>
      </div>
      {item.low_confidence && <p className="flag">Low-confidence segmentation. Check the green boundary and correct it if needed.</p>}
      <div className="images">
        <figure><figcaption>Original</figcaption><img src={fileUrl(item.original)} alt="Original" /></figure>
        <figure onClick={add}>
          <figcaption>Processed (green line = wound boundary)</figcaption>
          <img ref={ref} src={fileUrl(item.overlay) + "?t=" + item.area_px} alt="Processed"
               style={{ cursor: drawing ? "crosshair" : "default" }} />
        </figure>
        {c && (
          <figure><figcaption>Compared with previous (green = reduced, red = new)</figcaption>
            <img src={fileUrl(c.diff)} alt="Difference" /></figure>
        )}
      </div>
      {c && c.pct_change != null && (
        <p>Visible wound area is <b>{Math.abs(c.pct_change).toFixed(1)}% {c.pct_change >= 0 ? "smaller" : "larger"}</b> than in the previous photo.
          {!c.aligned && <span className="flag"> Automatic alignment failed, so wound centres were aligned instead; treat this value with caution.</span>}</p>
      )}
      {!drawing ? (
        <button className="ghost" onClick={() => setDrawing(true)}>Correct boundary</button>
      ) : (
        <div className="row">
          <span>Click around the wound on the processed image ({poly.length} points)</span>
          <button disabled={poly.length < 3} onClick={save}>Save boundary</button>
          <button className="ghost" onClick={() => { setDrawing(false); setPoly([]); }}>Cancel</button>
        </div>
      )}
      {err && <p className="error">{err}</p>}
    </div>
  );
}
