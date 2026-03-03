export async function postControl(action) {
  const res = await fetch(`/api/control/${action}`, {
    method: "POST",
  });
  return res.json();
}
