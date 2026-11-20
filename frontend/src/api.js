export const BASE = "http://localhost:5000";
export const fileUrl = (p) => BASE + p;

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, {
    method, headers, body: body ? JSON.stringify(body) : form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.msg || "Request failed");
  return data;
}

export async function downloadReport(wid) {
  const res = await fetch(`${BASE}/api/wounds/${wid}/report.pdf`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
  });
  if (!res.ok) { alert("Could not create report"); return; }
  const url = URL.createObjectURL(await res.blob());
  Object.assign(document.createElement("a"), { href: url, download: `smartheal_wound_${wid}.pdf` }).click();
}
