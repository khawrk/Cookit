export interface User {
  id: string;
  email: string;
  name: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name?: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}
