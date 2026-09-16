"use client";

import {FormEvent, useEffect, useState} from "react";

import {ErrorBox} from "@/components/common/ErrorBox";
import {fetchActiveOrganizations, registerAccount, type Organization, type RegisterPayload} from "@/lib/api";

type RegisterScreenProps = {
  error: string;
  loading: boolean;
  onRegister: (payload: RegisterPayload) => Promise<void>;
  onSwitchToLogin: () => void;
};

export function RegisterScreen({error, loading, onRegister, onSwitchToLogin}: RegisterScreenProps) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [organizationId, setOrganizationId] = useState<string>("");

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchActiveOrganizations();
        setOrganizations(data);
        if (data.length > 0) {
          setOrganizationId(String(data[0].id));
        }
      } catch {
        setOrganizations([]);
      }
    })();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!organizationId) {
      return;
    }

    await onRegister({
      username,
      email,
      password,
      first_name: firstName,
      last_name: lastName,
      organization: Number(organizationId),
    });
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>Đăng ký tài khoản</h1>
        <p>Chọn tổ chức của bạn. Vai trò sẽ được đặt mặc định là Employee.</p>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="username">Tên đăng nhập</label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              autoComplete="email"
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
              autoComplete="new-password"
              type="password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <div
            className="field-row"
            style={{
              display: "flex",
              gap: "16px",
              width: "100%",
            }}
          >
            <div
              className="field"
              style={{
                flex: 1,
                minWidth: 0,
              }}
            >
              <label htmlFor="first-name">Họ</label>
              <input
                id="first-name"
                autoComplete="given-name"
                value={firstName}
                onChange={(event) => setFirstName(event.target.value)}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div
              className="field"
              style={{
                flex: 1,
                minWidth: 0,
              }}
            >
              <label htmlFor="last-name">Tên</label>
              <input
                id="last-name"
                autoComplete="family-name"
                value={lastName}
                onChange={(event) => setLastName(event.target.value)}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                }}
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="organization">Tổ chức</label>
            <select
              id="organization"
              value={organizationId}
              onChange={(event) => setOrganizationId(event.target.value)}
              required
            >
              {organizations.length === 0 ? (
                <option value="">Không có tổ chức khả dụng</option>
              ) : (
                organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.name}
                  </option>
                ))
              )}
            </select>
          </div>

          {error ? <ErrorBox message={error} /> : null}

          <button className="primary-button" disabled={loading || organizations.length === 0} type="submit">
            {loading ? "Đang đăng ký" : "Đăng ký"}
          </button>

          <button className="text-button" disabled={loading} type="button" onClick={onSwitchToLogin}>
            Đã có tài khoản? Đăng nhập
          </button>
        </div>
      </form>
    </main>
  );
}
