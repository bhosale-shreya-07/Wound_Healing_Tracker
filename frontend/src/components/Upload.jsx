import { useRef, useState } from "react";
import { api } from "../api";

export default function Upload({ woundId, onDone }) {
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState(null);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [pts, setPts] = useState([]);   // calibration clicks, in natural image pixels
  const [cm, setCm] = useState(2);
  const [msg, setMsg] = useState("");
  const imgRef = useRef();

  const pick = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setMsg("");
    if (!f.type.startsWith("image/")) { setFile(null); setUrl(null); setMsg("Choose an image file."); return; }
    if (f.size > 16 * 1024 * 1024) { setFile(null); setUrl(null); setMsg("Image is too large. Choose a file under 16 MB."); return; }
    if (url) URL.revokeObjectURL(url);
    setFile(f); setUrl(URL.createObjectURL(f)); setPts([]);
  };
  const click = (e) => {
    const im = imgRef.current, r = im.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * im.naturalWidth;
    const y = ((e.clientY - r.top) / r.height) * im.naturalHeight;
    setPts((p) => (p.length >= 2 ? [{ x, y }] : [...p, { x, y }]));
  };

  const submit = async () => {
    if (!file) return;
    if (new Date(date + "T00:00:00") > new Date(new Date().toDateString())) {
      setMsg("Photo date cannot be in the future."); return;
    }
    const fd = new FormData();
    fd.append("image", file);
    fd.append("captured_on", date);
    if (pts.length === 2)
      fd.append("calib", JSON.stringify({ x1: pts[0].x, y1: pts[0].y, x2: pts[1].x, y2: pts[1].y, known_cm: Number(cm) }));
    setMsg("Processing...");
    try {
      await api(`/api/wounds/${woundId}/images`, { method: "POST", form: fd });
      setMsg("Analysis complete");
      if (url) URL.revokeObjectURL(url);
      setFile(null); setUrl(null); setPts([]);
      onDone();
    } catch (e) { setMsg(e.message); }
  };

  return (
    <div className="panel">
      <h3>Add a wound photo</h3>
      <div className="row">
        <input type="file" accept="image/*" onChange={pick} />
        <label>Photo date <input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
      </div>
      {url && (
        <>
          <p className="muted">
            To measure in cm, place a ruler or coin beside the wound, then click its two ends.
            Known length (cm): <input type="number" value={cm} step="0.1" min="0.1" onChange={(e) => setCm(e.target.value)} style={{ width: 70 }} />{" "}
            {pts.length === 2 ? "Calibrated" : `${pts.length}/2 points`}
          </p>
          <img ref={imgRef} src={url} onClick={click} className="calib-img" alt="Uploaded wound" />
        </>
      )}
      <div className="row" style={{ marginTop: 10 }}>
        <button disabled={!file || msg === "Processing..."} onClick={submit}>{msg === "Processing..." ? "Analyzing?" : "Analyze photo"}</button>
        <span className={msg && msg !== "Processing..." && msg !== "Analysis complete" ? "error" : "muted"}>{msg}</span>
      </div>
      <p className="muted">Keep the camera roughly perpendicular to the wound, at a similar distance and in similar lighting each time.</p>
    </div>
  );
}
