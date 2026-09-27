"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/http";
import { login, registerAccount } from "@/lib/auth";

type FieldName = "email" | "password" | "name" | "phone" | "address";

const EMPTY_FIELDS: Record<FieldName, string> = {
  email: "",
  password: "",
  name: "",
  phone: "",
  address: "",
};

function validate(values: Record<FieldName, string>): Partial<Record<FieldName, string>> {
  const errors: Partial<Record<FieldName, string>> = {};
  const email = values.email.trim();
  if (!email) errors.email = "Enter your email.";
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = "Enter a valid email address.";
  if (!values.password) errors.password = "Enter a password.";
  return errors;
}

export function RegisterForm() {
  const router = useRouter();
  const [values, setValues] = useState(EMPTY_FIELDS);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function update(field: FieldName, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const nextErrors = validate(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setPending(true);
    try {
      await registerAccount({
        email: values.email.trim(),
        password: values.password,
        name: values.name.trim(),
        phone: values.phone.trim(),
        address: values.address.trim(),
      });
      await login(values.email.trim(), values.password);
      router.replace("/");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setErrors(caught.fields);
        const shownOnField = Object.values(caught.fields).includes(caught.message);
        setFormError(shownOnField ? null : caught.message);
      } else {
        setFormError(caught instanceof Error ? caught.message : "Registration failed.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {formError && (
        <Alert variant="destructive">
          <AlertTitle>Could not create the account</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      <Field
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        value={values.email}
        error={errors.email}
        onChange={(value) => update("email", value)}
      />
      <Field
        id="password"
        label="Password"
        type="password"
        autoComplete="new-password"
        value={values.password}
        error={errors.password}
        onChange={(value) => update("password", value)}
      />
      <Field
        id="name"
        label="Name"
        autoComplete="name"
        value={values.name}
        error={errors.name}
        onChange={(value) => update("name", value)}
        optional
      />
      <Field
        id="phone"
        label="Phone"
        type="tel"
        autoComplete="tel"
        value={values.phone}
        error={errors.phone}
        onChange={(value) => update("phone", value)}
        optional
      />
      <Field
        id="address"
        label="Address"
        autoComplete="street-address"
        value={values.address}
        error={errors.address}
        onChange={(value) => update("address", value)}
        optional
      />
      <Button type="submit" className="w-full" disabled={pending}>
        {pending ? "Creating account…" : "Create account"}
      </Button>
      <p className="text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}

function Field({
  id,
  label,
  error,
  hint,
  optional,
  onChange,
  ...props
}: React.ComponentProps<"input"> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  optional?: boolean;
  onChange: (value: string) => void;
}) {
  const describedBy = [error ? `${id}-error` : null, hint ? `${id}-hint` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <Label htmlFor={id}>{label}</Label>
        {optional ? <span className="text-xs text-muted-foreground">Optional</span> : null}
      </div>
      <Input
        id={id}
        name={id}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        onChange={(event) => onChange(event.target.value)}
        {...props}
      />
      {hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
