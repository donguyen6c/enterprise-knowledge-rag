import {FormEvent, useState} from "react";

import {ErrorBox} from "@/components/common/ErrorBox";

type LoginScreenProps = {
  error: string;
  loading: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
};

export function LoginScreen({error, loading, onLogin}: LoginScreenProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onLogin(email, password);
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>Enterprise Knowledge RAG</h1>
        <p>Đăng nhập để hỏi đáp trên tài liệu bạn có quyền truy cập.</p>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              autoComplete="email"
              placeholder="admin@ou.edu.vn"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Mật khẩu</label>
            <input
              id="password"
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? <ErrorBox message={error} /> : null}

          <button className="primary-button" disabled={loading} type="submit">
            {loading ? "Đang đăng nhập" : "Đăng nhập"}
          </button>
        </div>
      </form>
    </main>
  );
}
