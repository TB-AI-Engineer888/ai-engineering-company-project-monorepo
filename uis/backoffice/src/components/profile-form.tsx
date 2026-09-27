"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/http";
import { fetchMe, updateProfile, type Profile } from "@/lib/auth";

const EMPTY: Profile = { name: "", phone: "", address: "" };

export function ProfileForm() {
  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState<Profile>(EMPTY);
  const [errors, setErrors] = useState<Partial<Profile>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const account = await fetchMe();
        if (cancelled) return;
        setEmail(account.email);
        setProfile(account.profile);
      } catch (caught) {
        if (!cancelled) {
          setLoadError(caught instanceof Error ? caught.message : "Could not load your profile.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  function update(field: keyof Profile, value: string) {
    setProfile((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSaved(false);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveError(null);
    setSaved(false);
    setPending(true);
    try {
      const account = await updateProfile({
        name: profile.name.trim(),
        phone: profile.phone.trim(),
        address: profile.address.trim(),
      });
      setEmail(account.email);
      setProfile(account.profile);
      setSaved(true);
    } catch (caught) {
      if (caught instanceof ApiError) {
        setErrors(caught.fields);
        setSaveError(caught.message);
      } else {
        setSaveError(caught instanceof Error ? caught.message : "Could not save your profile.");
      }
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading your account…</p>;
  }

  if (loadError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Profile unavailable</AlertTitle>
        <AlertDescription>{loadError}</AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {saveError && (
        <Alert variant="destructive">
          <AlertTitle>Could not save</AlertTitle>
          <AlertDescription>{saveError}</AlertDescription>
        </Alert>
      )}
      {saved && (
        <Alert>
          <AlertTitle>Profile saved</AlertTitle>
          <AlertDescription>Name and contact details were updated.</AlertDescription>
        </Alert>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" value={email} readOnly />
      </div>
      <ProfileField id="name" label="Name" autoComplete="name" value={profile.name} error={errors.name} onChange={(value) => update("name", value)} />
      <ProfileField id="phone" label="Phone" type="tel" autoComplete="tel" value={profile.phone} error={errors.phone} onChange={(value) => update("phone", value)} />
      <ProfileField id="address" label="Address" autoComplete="street-address" value={profile.address} error={errors.address} onChange={(value) => update("address", value)} />
      <Button type="submit" disabled={pending}>
        {pending ? "Saving…" : "Save profile"}
      </Button>
    </form>
  );
}

function ProfileField({
  id,
  label,
  error,
  onChange,
  ...props
}: React.ComponentProps<"input"> & {
  id: string;
  label: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        name={id}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
      {error ? (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
