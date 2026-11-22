export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export const PORTAL_MIRROR_URL = `${API_BASE_URL}/mirror`;
