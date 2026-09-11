import {User} from "@/lib/api";

export type StoredAuth = {
  access: string;
  refresh: string;
  user: User;
};
