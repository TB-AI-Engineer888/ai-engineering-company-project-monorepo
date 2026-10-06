"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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

  const loadAccount = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const account = await fetchMe();
      setEmail(account?.email ?? "");
      setProfile(account?.profile ?? EMPTY);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "";
      setLoadError(
        message && !/traceback|request failed|\b[1-5]\d\d\b/i.test(message)
          ? message
          : "Your profile could not be loaded. Try again, or contact HealthCore support.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const account = await fetchMe();
        if (cancelled) return;
        setEmail(account?.email ?? "");
        setProfile(account?.profile ?? EMPTY);
      } catch (caught) {
        if (cancelled) return;
        const message = caught instanceof Error ? caught.message : "";
        setLoadError(
          message && !/traceback|request failed|\b[1-5]\d\d\b/i.test(message)
            ? message
            : "Your profile could not be loaded. Try again, or contact HealthCore support.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
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
      const saved = await updateProfile({
        name: profile.name.trim(),
        phone: profile.phone.trim(),
        address: profile.address.trim(),
      });
      setProfile(saved);
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
        <AlertDescription>
          <p>{loadError}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" onClick={() => void loadAccount()}>
              Try again
            </Button>
            <Link href="/" className="underline underline-offset-4">
              Back to operations overview
            </Link>
          </div>
          <p className="mt-2">If this keeps happening, contact HealthCore support.</p>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {saveError && (
        <Alert variant="destructive">
          <AlertTitle>Could not save</AlertTitle>
          <AlertDescription>
            <p>{saveError}</p>
            <p className="mt-2">Use Save profile to try again, or contact HealthCore support if it continues.</p>
          </AlertDescription>
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
