import {useCallback, useEffect, useState} from "react";

import {
  AdminOrganizationPayload,
  AdminUser,
  AdminUserPayload,
  createAdminOrganization,
  createAdminUser,
  fetchAdminOrganizations,
  fetchAdminUsers,
  Organization,
  updateAdminOrganization,
  updateAdminUser
} from "@/lib/api";

type AdminRole = "SYSTEM_ADMIN" | "ORG_ADMIN";

export function useAdmin(
  token: string | null,
  role: string | undefined,
  activeView: "chat" | "documents" | "admin"
) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const canAccessAdmin =
    role === "SYSTEM_ADMIN" || role === "ORG_ADMIN";
  const isSystemAdmin = role === "SYSTEM_ADMIN";

  const loadAdminData = useCallback(async () => {
    if (!token || !canAccessAdmin) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const nextUsers = await fetchAdminUsers(token);
      setUsers(nextUsers);

      if (isSystemAdmin) {
        setOrganizations(await fetchAdminOrganizations(token));
      } else {
        setOrganizations([]);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Không tải được dữ liệu quản trị."
      );
    } finally {
      setLoading(false);
    }
  }, [canAccessAdmin, isSystemAdmin, token]);

  useEffect(() => {
    if (activeView === "admin") {
      void loadAdminData();
    }
  }, [activeView, loadAdminData]);

  const createUser = useCallback(
    async (payload: AdminUserPayload) => {
      if (!token) {
        return false;
      }

      setSaving(true);
      setError("");

      try {
        const user = await createAdminUser(token, payload);
        setUsers((current) => [...current, user].sort((a, b) => a.email.localeCompare(b.email)));
        return true;
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không tạo được người dùng."
        );
        return false;
      } finally {
        setSaving(false);
      }
    },
    [token]
  );

  const toggleUserActive = useCallback(
    async (user: AdminUser) => {
      if (!token) {
        return;
      }

      setSaving(true);
      setError("");

      try {
        const updatedUser = await updateAdminUser(token, user.id, {
          is_active: !user.is_active
        });
        setUsers((current) =>
          current.map((item) => (item.id === updatedUser.id ? updatedUser : item))
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không cập nhật được người dùng."
        );
      } finally {
        setSaving(false);
      }
    },
    [token]
  );

  const updateUserRole = useCallback(
    async (user: AdminUser, nextRole: AdminUser["role"]) => {
      if (!token || user.role === nextRole) {
        return;
      }

      setSaving(true);
      setError("");

      try {
        const updatedUser = await updateAdminUser(token, user.id, {
          role: nextRole as AdminUserPayload["role"]
        });
        setUsers((current) =>
          current.map((item) => (item.id === updatedUser.id ? updatedUser : item))
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không cập nhật được vai trò người dùng."
        );
      } finally {
        setSaving(false);
      }
    },
    [token]
  );

  const createOrganization = useCallback(
    async (payload: AdminOrganizationPayload) => {
      if (!token || !isSystemAdmin) {
        return false;
      }

      setSaving(true);
      setError("");

      try {
        const organization = await createAdminOrganization(token, payload);
        setOrganizations((current) =>
          [...current, organization].sort((a, b) => a.name.localeCompare(b.name))
        );
        return true;
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không tạo được tổ chức."
        );
        return false;
      } finally {
        setSaving(false);
      }
    },
    [isSystemAdmin, token]
  );

  const toggleOrganizationActive = useCallback(
    async (organization: Organization) => {
      if (!token || !isSystemAdmin) {
        return;
      }

      setSaving(true);
      setError("");

      try {
        const updatedOrganization = await updateAdminOrganization(token, organization.id, {
          is_active: !organization.is_active
        });
        setOrganizations((current) =>
          current.map((item) =>
            item.id === updatedOrganization.id ? updatedOrganization : item
          )
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Không cập nhật được tổ chức."
        );
      } finally {
        setSaving(false);
      }
    },
    [isSystemAdmin, token]
  );

  return {
    canAccessAdmin,
    createOrganization,
    createUser,
    error,
    isSystemAdmin,
    loadAdminData,
    loading,
    organizations,
    saving,
    toggleOrganizationActive,
    toggleUserActive,
    updateUserRole,
    users
  };
}
