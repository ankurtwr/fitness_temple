// Central API helper
// When testing on a physical phone on your Wi-Fi, use your PC's IP (e.g., http://10.29.33.146:8000)
// For Android emulator: use http://10.0.2.2:8000
// For Web or iOS Simulator: use http://localhost:8000
export const BASE_URL = "http://10.29.33.146:8000";

let _token = null;

export function setToken(t) { _token = t; }
export function getToken() { return _token; }

async function request(method, path, body = null, isForm = false) {
  const headers = { Accept: "application/json" };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;
  if (isForm) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body) {
    headers["Content-Type"] = "application/json";
  }

  const opts = { method, headers };
  if (body) {
    if (isForm) {
      opts.body = new URLSearchParams(body).toString();
    } else {
      opts.body = JSON.stringify(body);
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, opts);
  const data = await res.json();
  return { status: res.status, data };
}

// ── Auth ──
export const login = (username, password) =>
  request("POST", "/api/login", { username, password }, true);

// ── Members ──
export const getMembers = (search = "") =>
  request("GET", `/api/members${search ? `?search=${encodeURIComponent(search)}` : ""}`);

export const getMember = (id) => request("GET", `/api/members/${id}`);

export const createMember = (fields) =>
  request("POST", "/api/members", fields, true);

export const getPlans = () => request("GET", "/api/plans");

export const startCardAssignment = (memberId) =>
  request("POST", `/api/members/${memberId}/assign-card`, { csrf_token: "" }, true);

export const checkAssignmentStatus = (assignmentId) =>
  request("GET", `/api/assign/status?assignment_id=${assignmentId}`);

export const renewMembership = (memberId, planId, amountPaid) =>
  request("POST", `/api/members/${memberId}/renew`, { plan_id: planId, amount_paid: amountPaid, csrf_token: "" }, true);

// ── Attendance ──
export const getTodayAttendance = () =>
  request("GET", "/api/attendance/today");
