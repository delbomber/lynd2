import { useState, useEffect } from "react";
import {
  Settings,
  Phone,
  PhoneCall,
  Loader2,
  MessageSquare,
  ClipboardCheck,
  UserCheck,
  ArrowLeft,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

type Status = "idle" | "sending" | "success" | "error";

const STORAGE_KEY = "demo_api_url";

const colors = {
  navy900: "hsl(220, 40%, 13%)",
  navy800: "hsl(220, 35%, 18%)",
  navy700: "hsl(220, 30%, 25%)",
  teal500: "hsl(174, 60%, 45%)",
  teal400: "hsl(174, 55%, 55%)",
  teal600: "hsl(174, 65%, 35%)",
  white: "hsl(0, 0%, 100%)",
  gray300: "hsl(220, 15%, 75%)",
  gray400: "hsl(220, 10%, 55%)",
  red500: "hsl(0, 70%, 55%)",
  green500: "hsl(145, 60%, 45%)",
};

export default function Demo() {
  const [phoneDigits, setPhoneDigits] = useState("");
  const [firstName, setFirstName] = useState("Jane");
  const [lastName, setLastName] = useState("Smith");
  const [dob, setDob] = useState("1982-12-01");
  const [referringProvider, setReferringProvider] = useState("Doctor Jones");
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem(STORAGE_KEY) || "");
  const [showSettings, setShowSettings] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, apiUrl);
  }, [apiUrl]);

  const formatPhone = (digits: string): string => {
    if (!digits) return "";
    if (digits.length <= 3) return `(${digits}`;
    if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, "").slice(0, 10);
    setPhoneDigits(raw);
  };

  const canSubmit = phoneDigits.length === 10 && firstName.trim().length > 0 && apiUrl.trim().length > 0 && status !== "sending";

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setStatus("sending");
    setErrorMsg("");

    const baseUrl = apiUrl.replace(/\/+$/, "");
    const body = {
      patient: {
        first_name: firstName,
        last_name: lastName,
        phone: `+1${phoneDigits}`,
        date_of_birth: dob,
      },
      study_id: "DEMO-001",
      referring_provider: referringProvider,
    };

    try {
      const res = await fetch(`${baseUrl}/api/v1/referrals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
      }

      setStatus("success");
    } catch (err: any) {
      setErrorMsg(err.message || "Network error");
      setStatus("error");
    }
  };

  const reset = () => {
    setStatus("idle");
    setPhoneDigits("");
    setErrorMsg("");
  };

  return (
    <div style={{ minHeight: "100vh", background: colors.navy900, color: colors.white }}>
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "16px 24px",
          borderBottom: `1px solid ${colors.navy700}`,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.02em" }}>
          Lynd Clinical
        </span>
        <a
          href="/"
          style={{
            color: colors.gray300,
            textDecoration: "none",
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <ArrowLeft size={14} />
          Back to Deck
        </a>
      </header>

      {/* Main Content */}
      <main
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "48px 16px",
          gap: 32,
        }}
      >
        {/* Card */}
        <div
          style={{
            background: colors.navy800,
            border: `1px solid ${colors.navy700}`,
            borderRadius: 16,
            padding: 32,
            width: "100%",
            maxWidth: 480,
            position: "relative",
          }}
        >
          {/* Settings Toggle */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              background: "none",
              border: "none",
              cursor: "pointer",
              color: showSettings ? colors.teal400 : colors.gray400,
              padding: 4,
            }}
            aria-label="API Settings"
          >
            {showSettings ? <X size={18} /> : <Settings size={18} />}
          </button>

          {/* Settings Panel */}
          {showSettings && (
            <div
              style={{
                marginBottom: 24,
                padding: 16,
                background: colors.navy700,
                borderRadius: 8,
              }}
            >
              <label
                style={{ display: "block", fontSize: 12, color: colors.gray300, marginBottom: 8 }}
              >
                Pilot Server URL
              </label>
              <input
                type="url"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://pilot.example.com"
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: `1px solid ${colors.navy700}`,
                  background: colors.navy900,
                  color: colors.white,
                  fontSize: 14,
                  outline: "none",
                }}
              />
            </div>
          )}

          {/* Title */}
          <div style={{ textAlign: "center", marginBottom: 28 }}>
            <Phone
              size={36}
              style={{ color: colors.teal500, marginBottom: 12 }}
            />
            <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>
              Try the Voice Agent
            </h1>
            <p style={{ fontSize: 14, color: colors.gray300 }}>
              Enter your number and we'll call you with a live demo
            </p>
          </div>

          {/* Status: Idle / Sending */}
          {(status === "idle" || status === "sending") && (
            <>
              <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: 13, color: colors.gray300, marginBottom: 6 }}>
                    First name
                  </label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    disabled={status === "sending"}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: `1px solid ${colors.navy700}`,
                      background: colors.navy900,
                      color: colors.white,
                      fontSize: 14,
                      outline: "none",
                      opacity: status === "sending" ? 0.5 : 1,
                    }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: "block", fontSize: 13, color: colors.gray300, marginBottom: 6 }}>
                    Last name
                  </label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    disabled={status === "sending"}
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: `1px solid ${colors.navy700}`,
                      background: colors.navy900,
                      color: colors.white,
                      fontSize: 14,
                      outline: "none",
                      opacity: status === "sending" ? 0.5 : 1,
                    }}
                  />
                </div>
              </div>
              <label style={{ display: "block", fontSize: 13, color: colors.gray300, marginBottom: 6 }}>
                Date of birth
              </label>
              <input
                type="date"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
                disabled={status === "sending"}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: `1px solid ${colors.navy700}`,
                  background: colors.navy900,
                  color: colors.white,
                  fontSize: 14,
                  outline: "none",
                  marginBottom: 12,
                  opacity: status === "sending" ? 0.5 : 1,
                }}
              />
              <label style={{ display: "block", fontSize: 13, color: colors.gray300, marginBottom: 6 }}>
                Referring provider
              </label>
              <input
                type="text"
                value={referringProvider}
                onChange={(e) => setReferringProvider(e.target.value)}
                disabled={status === "sending"}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: `1px solid ${colors.navy700}`,
                  background: colors.navy900,
                  color: colors.white,
                  fontSize: 14,
                  outline: "none",
                  marginBottom: 12,
                  opacity: status === "sending" ? 0.5 : 1,
                }}
              />
              <label
                htmlFor="phone"
                style={{ display: "block", fontSize: 13, color: colors.gray300, marginBottom: 6 }}
              >
                Phone number
              </label>
              <input
                id="phone"
                type="tel"
                value={formatPhone(phoneDigits)}
                onChange={handlePhoneChange}
                placeholder="(555) 123-4567"
                disabled={status === "sending"}
                style={{
                  width: "100%",
                  padding: "14px 16px",
                  borderRadius: 10,
                  border: `1px solid ${colors.navy700}`,
                  background: colors.navy900,
                  color: colors.white,
                  fontSize: 18,
                  letterSpacing: "0.02em",
                  outline: "none",
                  marginBottom: 16,
                  opacity: status === "sending" ? 0.5 : 1,
                }}
              />
              <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                style={{
                  width: "100%",
                  padding: "14px 0",
                  borderRadius: 10,
                  border: "none",
                  background: canSubmit ? colors.teal500 : colors.navy700,
                  color: canSubmit ? colors.white : colors.gray400,
                  fontSize: 16,
                  fontWeight: 600,
                  cursor: canSubmit ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  transition: "background 0.15s",
                }}
              >
                {status === "sending" ? (
                  <>
                    <Loader2 size={18} className="spin" />
                    Calling...
                  </>
                ) : (
                  <>
                    <PhoneCall size={18} />
                    Call Me
                  </>
                )}
              </button>
            </>
          )}

          {/* Status: Success */}
          {status === "success" && (
            <div style={{ textAlign: "center" }}>
              <CheckCircle2
                size={48}
                style={{ color: colors.green500, marginBottom: 16 }}
              />
              <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
                Call initiated!
              </h2>
              <p style={{ fontSize: 14, color: colors.gray300, marginBottom: 24 }}>
                Your phone should ring within 30 seconds.
              </p>
              <button
                onClick={reset}
                style={{
                  padding: "10px 24px",
                  borderRadius: 8,
                  border: `1px solid ${colors.navy700}`,
                  background: "transparent",
                  color: colors.teal400,
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Try Again
              </button>
            </div>
          )}

          {/* Status: Error */}
          {status === "error" && (
            <div style={{ textAlign: "center" }}>
              <AlertCircle
                size={48}
                style={{ color: colors.red500, marginBottom: 16 }}
              />
              <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
                Something went wrong
              </h2>
              <p
                style={{
                  fontSize: 13,
                  color: colors.red500,
                  marginBottom: 24,
                  padding: "8px 12px",
                  background: "hsla(0, 70%, 55%, 0.1)",
                  borderRadius: 6,
                  wordBreak: "break-all",
                }}
              >
                {errorMsg}
              </p>
              <button
                onClick={reset}
                style={{
                  padding: "10px 24px",
                  borderRadius: 8,
                  border: `1px solid ${colors.navy700}`,
                  background: "transparent",
                  color: colors.teal400,
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                Try Again
              </button>
            </div>
          )}

          {/* No API URL Warning */}
          {!apiUrl && status === "idle" && (
            <p
              style={{
                marginTop: 12,
                fontSize: 12,
                color: colors.gray400,
                textAlign: "center",
              }}
            >
              Configure your pilot server URL via the{" "}
              <button
                onClick={() => setShowSettings(true)}
                style={{
                  background: "none",
                  border: "none",
                  color: colors.teal400,
                  cursor: "pointer",
                  fontSize: 12,
                  textDecoration: "underline",
                  padding: 0,
                }}
              >
                settings
              </button>{" "}
              panel.
            </p>
          )}
        </div>

        {/* What to Expect */}
        <div
          style={{
            background: colors.navy800,
            border: `1px solid ${colors.navy700}`,
            borderRadius: 16,
            padding: 28,
            width: "100%",
            maxWidth: 480,
          }}
        >
          <h2
            style={{
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 20,
              color: colors.gray300,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            What to Expect
          </h2>
          {[
            { icon: PhoneCall, text: "Your phone will ring within 30 seconds" },
            { icon: MessageSquare, text: "An AI agent will introduce the study" },
            { icon: ClipboardCheck, text: "You'll walk through a brief pre-screening" },
            { icon: UserCheck, text: 'Say "speak to a person" at any time to escalate' },
          ].map(({ icon: Icon, text }, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 14,
                marginBottom: i < 3 ? 16 : 0,
              }}
            >
              <Icon size={18} style={{ color: colors.teal500, marginTop: 2, flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: colors.gray300, lineHeight: 1.5 }}>{text}</span>
            </div>
          ))}
        </div>
      </main>

      {/* Spin animation for loader */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
        input::placeholder {
          color: ${colors.gray400};
        }
        input:focus {
          border-color: ${colors.teal500} !important;
        }
        button:hover:not(:disabled) {
          filter: brightness(1.1);
        }
      `}</style>
    </div>
  );
}
