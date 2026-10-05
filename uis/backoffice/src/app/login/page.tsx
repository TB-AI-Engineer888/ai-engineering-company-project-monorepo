import { AuthFrame } from "@/components/auth-frame";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <AuthFrame title="Sign in">
      <LoginForm />
    </AuthFrame>
  );
}
