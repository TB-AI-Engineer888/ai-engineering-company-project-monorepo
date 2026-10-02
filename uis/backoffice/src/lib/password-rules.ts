export function passwordConfirmationError(password: string, confirmation: string) {
  if (password !== confirmation) {
    return "New password and confirmation do not match.";
  }
  if (password.length < 8) {
    return "Use at least 8 characters.";
  }
  return null;
}
