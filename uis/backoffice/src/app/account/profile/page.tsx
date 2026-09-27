import { ProfileForm } from "@/components/profile-form";
import { Card, CardContent } from "@/components/ui/card";

export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-xl">
      <h2 className="mb-6 text-2xl font-semibold tracking-tight">Account profile</h2>
      <Card>
        <CardContent>
          <ProfileForm />
        </CardContent>
      </Card>
    </div>
  );
}
