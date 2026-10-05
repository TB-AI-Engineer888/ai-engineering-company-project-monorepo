import { AuthFrame } from "@/components/auth-frame";
import { RegisterForm } from "@/components/register-form";

export default function RegisterPage() {
  return (
    <AuthFrame title="Register">
      <RegisterForm />
    </AuthFrame>
  );
}
