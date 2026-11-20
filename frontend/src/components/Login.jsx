import { useState } from "react";
import { api } from "../api";

export default function Login({ onAuth }) {
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [reg, setReg] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async () => {
    try {
      const d = await api(`/api/auth/${reg ? "register" : "login"}`, { method: "POST", body: f });
      localStorage.setItem("token", d.token);
      onAuth();
    } catch (e) { setErr(e.message); }
  };
  return (
    <div className="login">
      <h2>SmartHeal: {reg ? "Create account" : "Log in"}</h2>
      {reg && <input type="text" placeholder="Name" onChange={set("name")} />}
      <input type="email" placeholder="Email" onChange={set("email")} />
      <input type="password" placeholder="Password (6+ characters)" onChange={set("password")} />
      <button onClick={submit}>{reg ? "Create account" : "Log in"}</button>
      <a onClick={() => { setReg(!reg); setErr(""); }}>{reg ? "Already have an account? Log in" : "New here? Create an account"}</a>
      <p className="error">{err}</p>
    </div>
  );
}
