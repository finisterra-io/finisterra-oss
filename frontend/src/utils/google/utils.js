export async function getIdToken(refreshToken) {
  const requestOptions = {
    method: "POST",
    redirect: "follow",
  };

  const response = await fetch(
    `https://oauth2.googleapis.com/token?refresh_token=${refreshToken}&client_id=${process.env.GOOGLE_CLIENT_ID}&client_secret=${process.env.GOOGLE_CLIENT_SECRET}&grant_type=refresh_token&Content-Type=application/x-www-form-urlencoded`,
    requestOptions
  );
  const result = await response.json();

  return result.id_token;
}
