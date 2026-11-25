const DEVICE_KEY = "interview_device_id";

export function getDeviceId() {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

export function newRequestId() {
  return crypto.randomUUID();
}
