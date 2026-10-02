import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id_hash: string;
    username: string;
    role: string;
    agent_quota: number;
    workspace_id: string | null;
    access_token: string;
    refresh_token: string;
  }

  interface Session {
    user: {
      id_hash: string;
      username: string;
      email: string;
      role: string;
      agent_quota: number;
      workspace_id: string | null;
      access_token: string;
    };
    error?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id_hash: string;
    username: string;
    role: string;
    agent_quota: number;
    workspace_id: string | null;
    access_token: string;
    refresh_token: string;
    access_token_expires_at: number;
    error?: string;
  }
}
