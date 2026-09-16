import {FormEvent, useState} from "react";
import {Building2, Power, RefreshCw, ShieldCheck, UserPlus, UsersRound} from "lucide-react";

import {ErrorBox} from "@/components/common/ErrorBox";
import {EmptyState} from "@/components/common/EmptyState";
import {LoadingLine} from "@/components/common/LoadingLine";
import {
  AdminOrganizationPayload,
  AdminUser,
  AdminUserPayload,
  Organization
} from "@/lib/api";

type AdminDashboardProps = {
  error: string;
  currentUserId: number;
  isSystemAdmin: boolean;
  loading: boolean;
  onCreateOrganization: (payload: AdminOrganizationPayload) => Promise<boolean>;
  onCreateUser: (payload: AdminUserPayload) => Promise<boolean>;
  onRefresh: () => Promise<void>;
  onToggleOrganizationActive: (organization: Organization) => Promise<void>;
  onToggleUserActive: (user: AdminUser) => Promise<void>;
  onUpdateUserRole: (user: AdminUser, role: AdminUser["role"]) => Promise<void>;
  organizations: Organization[];
  saving: boolean;
  users: AdminUser[];
};

const roleLabels = {
  SYSTEM_ADMIN: "System Admin",
  ORG_ADMIN: "Organization Admin",
  EMPLOYEE: "Employee"
} as const;

export function AdminDashboard({
  error,
  currentUserId,
  isSystemAdmin,
  loading,
  onCreateOrganization,
  onCreateUser,
  onRefresh,
  onToggleOrganizationActive,
  onToggleUserActive,
  onUpdateUserRole,
  organizations,
  saving,
  users
}: AdminDashboardProps) {
  const [userForm, setUserForm] = useState({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    role: "EMPLOYEE" as AdminUserPayload["role"],
    organization: ""
  });
  const [organizationForm, setOrganizationForm] = useState({
    name: "",
    description: ""
  });

  const activeUsers = users.filter((user) => user.is_active).length;
  const activeOrganizations = organizations.filter(
    (organization) => organization.is_active
  ).length;

  async function submitUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const succeeded = await onCreateUser({
      username: userForm.username,
      email: userForm.email,
      password: userForm.password,
      first_name: userForm.first_name,
      last_name: userForm.last_name,
      role: userForm.role,
      organization:
        isSystemAdmin && userForm.organization
          ? Number(userForm.organization)
          : undefined
    });

    if (succeeded) {
      setUserForm({
        username: "",
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        role: "EMPLOYEE",
        organization: ""
      });
    }
  }

  async function submitOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const succeeded = await onCreateOrganization(organizationForm);

    if (succeeded) {
      setOrganizationForm({name: "", description: ""});
    }
  }

  return (
    <section className={`admin-view ${isSystemAdmin ? "system-admin" : "organization-admin"}`}>
      <div className="admin-heading">
        <div>
          <span className="eyebrow">Quản trị hệ thống</span>
          <h2>{isSystemAdmin ? "System Admin" : "Organization Admin"}</h2>
          <p>
            {isSystemAdmin
              ? "Quản lý tổ chức và toàn bộ tài khoản trong hệ thống."
              : "Quản lý các tài khoản thuộc tổ chức của bạn."}
          </p>
        </div>
        <button
          className="icon-button light"
          disabled={loading}
          onClick={() => void onRefresh()}
          title="Tải lại dữ liệu quản trị"
          type="button"
        >
          <RefreshCw size={17} />
        </button>
      </div>

      <div className={`admin-metrics ${isSystemAdmin ? "three-items" : "two-items"}`}>
        <article>
          <UsersRound size={20} />
          <div>
            <span>Tài khoản hoạt động</span>
            <strong>{activeUsers}/{users.length}</strong>
          </div>
        </article>
        <article>
          <ShieldCheck size={20} />
          <div>
            <span>Quyền hiện tại</span>
            <strong>{isSystemAdmin ? "System Admin" : "Organization Admin"}</strong>
          </div>
        </article>
        {isSystemAdmin ? (
          <article>
            <Building2 size={20} />
            <div>
              <span>Tổ chức hoạt động</span>
              <strong>{activeOrganizations}/{organizations.length}</strong>
            </div>
          </article>
        ) : null}
      </div>

      {error ? <ErrorBox message={error} /> : null}

      <div className={`admin-grid ${isSystemAdmin ? "two-columns" : "single-column"}`}>
        <section className="admin-card">
          <header className="admin-card-header">
            <div>
              <span className="eyebrow">Tài khoản</span>
              <h3>Tạo người dùng</h3>
            </div>
            <UserPlus size={19} />
          </header>

          <form className="admin-form" onSubmit={submitUser}>
            <div className="field-row">
              <div className="field">
                <label htmlFor="admin-first-name">Họ</label>
                <input
                  id="admin-first-name"
                  value={userForm.first_name}
                  onChange={(event) =>
                    setUserForm((current) => ({
                      ...current,
                      first_name: event.target.value
                    }))
                  }
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="admin-last-name">Tên</label>
                <input
                  id="admin-last-name"
                  value={userForm.last_name}
                  onChange={(event) =>
                    setUserForm((current) => ({
                      ...current,
                      last_name: event.target.value
                    }))
                  }
                  required
                />
              </div>
            </div>

            <div className="field">
              <label htmlFor="admin-username">Tên đăng nhập</label>
              <input
                id="admin-username"
                value={userForm.username}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    username: event.target.value
                  }))
                }
                required
              />
            </div>

            <div className="field">
              <label htmlFor="admin-email">Email</label>
              <input
                id="admin-email"
                type="email"
                value={userForm.email}
                onChange={(event) =>
                  setUserForm((current) => ({...current, email: event.target.value}))
                }
                required
              />
            </div>

            <div className="field">
              <label htmlFor="admin-password">Mật khẩu</label>
              <input
                id="admin-password"
                minLength={8}
                type="password"
                value={userForm.password}
                onChange={(event) =>
                  setUserForm((current) => ({
                    ...current,
                    password: event.target.value
                  }))
                }
                required
              />
            </div>

            <div className="field-row">
                <div className="field">
                  <label htmlFor="admin-role">Vai trò</label>
                  <select
                    id="admin-role"
                    value={userForm.role}
                    onChange={(event) =>
                      setUserForm((current) => ({
                        ...current,
                        role: event.target.value as AdminUserPayload["role"]
                      }))
                    }
                  >
                    <option value="EMPLOYEE">Employee</option>
                    <option value="ORG_ADMIN">Organization Admin</option>
                    {isSystemAdmin ? (
                      <option value="SYSTEM_ADMIN">System Admin</option>
                    ) : null}
                  </select>
                </div>
                {isSystemAdmin ? <div className="field">
                  <label htmlFor="admin-organization">Tổ chức</label>
                  <select
                    id="admin-organization"
                    disabled={userForm.role === "SYSTEM_ADMIN"}
                    value={userForm.organization}
                    onChange={(event) =>
                      setUserForm((current) => ({
                        ...current,
                        organization: event.target.value
                      }))
                    }
                    required={userForm.role !== "SYSTEM_ADMIN"}
                  >
                    <option value="">Chọn tổ chức</option>
                    {organizations
                      .filter((organization) => organization.is_active)
                      .map((organization) => (
                        <option key={organization.id} value={organization.id}>
                          {organization.name}
                        </option>
                      ))}
                  </select>
                </div> : null}
              </div>

            <button className="primary-button" disabled={saving} type="submit">
              <UserPlus size={16} />
              Tạo tài khoản
            </button>
          </form>
        </section>

        {isSystemAdmin ? (
          <section className="admin-card">
            <header className="admin-card-header">
              <div>
                <span className="eyebrow">Tổ chức</span>
                <h3>Tạo tổ chức</h3>
              </div>
              <Building2 size={19} />
            </header>

            <form className="admin-form" onSubmit={submitOrganization}>
              <div className="field">
                <label htmlFor="organization-name">Tên tổ chức</label>
                <input
                  id="organization-name"
                  value={organizationForm.name}
                  onChange={(event) =>
                    setOrganizationForm((current) => ({
                      ...current,
                      name: event.target.value
                    }))
                  }
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="organization-description">Mô tả</label>
                <textarea
                  id="organization-description"
                  value={organizationForm.description}
                  onChange={(event) =>
                    setOrganizationForm((current) => ({
                      ...current,
                      description: event.target.value
                    }))
                  }
                />
              </div>
              <button className="primary-button" disabled={saving} type="submit">
                <Building2 size={16} />
                Tạo tổ chức
              </button>
            </form>
          </section>
        ) : null}
      </div>

      <section className="admin-card admin-table-card">
        <header className="admin-card-header">
          <div>
            <span className="eyebrow">Tài khoản</span>
            <h3>Danh sách người dùng</h3>
          </div>
          <span className="admin-count">{users.length} tài khoản</span>
        </header>

        {loading ? (
          <LoadingLine>Đang tải dữ liệu quản trị...</LoadingLine>
        ) : users.length === 0 ? (
          <EmptyState>Chưa có người dùng trong phạm vi quản trị.</EmptyState>
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Người dùng</th>
                  <th>Vai trò</th>
                  <th>Tổ chức</th>
                  <th>Trạng thái</th>
                  <th aria-label="Thao tác" />
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <strong>{`${user.first_name} ${user.last_name}`.trim() || user.username}</strong>
                      <span>{user.email}</span>
                    </td>
                    <td>
                      <select
                        className="admin-role-select"
                        disabled={saving || user.id === currentUserId}
                        onChange={(event) =>
                          void onUpdateUserRole(
                            user,
                            event.target.value as AdminUser["role"]
                          )
                        }
                        title={
                          user.id === currentUserId
                            ? "Không thể thay đổi vai trò của chính bạn"
                            : "Cập nhật vai trò"
                        }
                        value={user.role}
                      >
                        <option value="EMPLOYEE">Employee</option>
                        <option value="ORG_ADMIN">Organization Admin</option>
                        {isSystemAdmin ? (
                          <option value="SYSTEM_ADMIN">System Admin</option>
                        ) : null}
                      </select>
                    </td>
                    <td>{user.organization_name || "Toàn hệ thống"}</td>
                    <td>
                      <span className={`admin-status ${user.is_active ? "active" : "inactive"}`}>
                        {user.is_active ? "Hoạt động" : "Đã khóa"}
                      </span>
                    </td>
                    <td>
                      {isSystemAdmin ? (
                        <button
                          className="text-button admin-action"
                          disabled={saving}
                          onClick={() => void onToggleUserActive(user)}
                          type="button"
                        >
                          <Power size={15} />
                          {user.is_active ? "Khóa" : "Kích hoạt"}
                        </button>
                      ) : <span className="admin-scope-note">Theo tổ chức</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {isSystemAdmin ? (
        <section className="admin-card admin-table-card">
          <header className="admin-card-header">
            <div>
              <span className="eyebrow">Tổ chức</span>
              <h3>Danh sách tổ chức</h3>
            </div>
            <span className="admin-count">{organizations.length} tổ chức</span>
          </header>

          {loading ? (
            <LoadingLine>Đang tải tổ chức...</LoadingLine>
          ) : organizations.length === 0 ? (
            <EmptyState>Chưa có tổ chức.</EmptyState>
          ) : (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Tổ chức</th>
                    <th>Trạng thái</th>
                    <th aria-label="Thao tác" />
                  </tr>
                </thead>
                <tbody>
                  {organizations.map((organization) => (
                    <tr key={organization.id}>
                      <td>
                        <strong>{organization.name}</strong>
                        <span>{organization.description || "Chưa có mô tả"}</span>
                      </td>
                      <td>
                        <span className={`admin-status ${organization.is_active ? "active" : "inactive"}`}>
                          {organization.is_active ? "Hoạt động" : "Đã khóa"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="text-button admin-action"
                          disabled={saving}
                          onClick={() => void onToggleOrganizationActive(organization)}
                          type="button"
                        >
                          <Power size={15} />
                          {organization.is_active ? "Khóa" : "Kích hoạt"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </section>
  );
}
