import { useState, useEffect } from "react";
import { Layers, Menu, X, Home as HomeIcon } from "lucide-react";

const NAV = [
  { label: "Home", anchor: null, isHome: true },
  { label: "Approvals", anchor: "features" },
  { label: "Schemes & Incentives", anchor: "incentives" },
  { label: "How It Works", anchor: "how-it-works" },
  { label: "Resources", anchor: "resources" },
];

function Header({ step, onNavigate, onGoHome }) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const handleNavClick = (item) => {
    if (item.isHome) {
      // Navigate to home page
      if (onGoHome) {
        onGoHome();
      } else {
        onNavigate(0);
      }
      setMobileOpen(false);
      return;
    }
    // Scroll to section on home page
    onNavigate(0);
    setTimeout(() => {
      document.getElementById(item.anchor)?.scrollIntoView({ behavior: "smooth" });
    }, 80);
    setMobileOpen(false);
  };

  const navBtnStyle = {
    fontSize: "0.875rem",
    fontWeight: 500,
    padding: "8px 12px",
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#2A3D4A",
    borderRadius: 6,
    transition: "color 0.15s, background 0.15s",
  };

  return (
    <>
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: scrolled ? "rgba(255,255,255,0.94)" : "#fff",
          backdropFilter: scrolled ? "blur(12px)" : "none",
          WebkitBackdropFilter: scrolled ? "blur(12px)" : "none",
          borderBottom: `1px solid ${scrolled ? "#C8D9E2" : "#DCE9EF"}`,
          transition: "background 0.2s, border-color 0.2s, box-shadow 0.2s",
          boxShadow: scrolled ? "0 1px 12px rgba(42,61,74,0.07)" : "none",
        }}
      >
        <div
          style={{
            maxWidth: 1160,
            margin: "0 auto",
            padding: "0 24px",
            height: 60,
            display: "flex",
            alignItems: "center",
            gap: 0,
          }}
        >
          {/* Logo */}
          <button
            onClick={() => (onGoHome ? onGoHome() : onNavigate(0))}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 9,
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
              marginRight: "auto",
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                background: "#2A3D4A",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Layers size={17} color="#fff" strokeWidth={2} />
            </div>
            <span
              style={{
                fontWeight: 700,
                fontSize: "0.9375rem",
                color: "#2A3D4A",
                letterSpacing: "-0.01em",
              }}
            >
              UdyogPermit
            </span>
          </button>

          {/* Desktop nav */}
          <nav
            style={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              marginRight: 20,
            }}
            className="desktop-nav"
          >
            {NAV.filter((n) => step === 0 || n.isHome).map((n) => (
              <button
                key={n.label}
                onClick={() => handleNavClick(n)}
                style={navBtnStyle}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "#5F8699";
                  e.currentTarget.style.background = "#E8F2F6";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "#2A3D4A";
                  e.currentTarget.style.background = "none";
                }}
              >
                {n.label}
              </button>
            ))}
          </nav>

          {/* Right actions — Get Started only, NO Login */}
          {step === 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }} className="desktop-nav">
              <button
                onClick={() => onNavigate(1)}
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  padding: "8px 16px",
                  background: "#5F8699",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  cursor: "pointer",
                  transition: "background 0.15s, transform 0.12s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#4A6E80";
                  e.currentTarget.style.transform = "translateY(-1px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#5F8699";
                  e.currentTarget.style.transform = "translateY(0)";
                }}
              >
                Get Started
              </button>
            </div>
          )}

          {/* Mobile hamburger */}
          <button
            className="mobile-menu-btn"
            onClick={() => setMobileOpen(true)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#2A3D4A",
              padding: 6,
              display: "none",
            }}
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
        </div>

        {/* Workflow progress bar — shown inside steps */}
        {step > 0 && (
          <div
            style={{
              borderTop: "1px solid #DCE9EF",
              background: "#F6EFE2",
            }}
          >
            <div
              style={{
                maxWidth: 1160,
                margin: "0 auto",
                padding: "0 24px",
                height: 40,
                display: "flex",
                alignItems: "center",
                gap: 0,
              }}
            >
              {[
                { n: 1, label: "Project Information" },
                { n: 2, label: "Profile Review" },
                { n: 3, label: "Approval Roadmap" },
              ].map((s, i) => (
                <div key={s.n} style={{ display: "flex", alignItems: "center" }}>
                  {i > 0 && <div style={{ width: 32, height: 1, background: "#C8D9E2", margin: "0 8px" }} />}
                  <button
                    onClick={() => step >= s.n && onNavigate(s.n)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      background: "none",
                      border: "none",
                      cursor: step >= s.n ? "pointer" : "default",
                      padding: 0,
                      color: step === s.n ? "#5F8699" : step > s.n ? "#2A3D4A" : "#7A96A5",
                    }}
                  >
                    <span
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: "50%",
                        background: step === s.n ? "#5F8699" : step > s.n ? "#3D8A6A" : "#C8D9E2",
                        color: step >= s.n ? "#fff" : "#7A96A5",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "0.6875rem",
                        fontWeight: 700,
                      }}
                    >
                      {step > s.n ? "\u2713" : s.n}
                    </span>
                    <span style={{ fontSize: "0.8125rem", fontWeight: step === s.n ? 600 : 400 }}>
                      {s.label}
                    </span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "#fff",
            zIndex: 100,
            display: "flex",
            flexDirection: "column",
            padding: "20px 24px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <div style={{ width: 30, height: 30, background: "#2A3D4A", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Layers size={16} color="#fff" strokeWidth={2} />
              </div>
              <span style={{ fontWeight: 700, fontSize: "0.9375rem", color: "#2A3D4A" }}>UdyogPermit</span>
            </div>
            <button
              onClick={() => setMobileOpen(false)}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}
            >
              <X size={22} color="#2A3D4A" />
            </button>
          </div>
          <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {NAV.filter((n) => step === 0 || n.isHome).map((n) => (
              <button
                key={n.label}
                onClick={() => handleNavClick(n)}
                style={{
                  textAlign: "left",
                  padding: "14px 0",
                  background: "none",
                  border: "none",
                  borderBottom: "1px solid #DCE9EF",
                  cursor: "pointer",
                  fontSize: "1rem",
                  fontWeight: 500,
                  color: "#2A3D4A",
                }}
              >
                {n.label}
              </button>
            ))}
          </nav>
          {step === 0 && (
            <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
              <button
                onClick={() => {
                  setMobileOpen(false);
                  onNavigate(1);
                }}
                style={{
                  padding: "12px 24px",
                  border: "none",
                  borderRadius: 10,
                  background: "#5F8699",
                  color: "#fff",
                  fontSize: "0.9375rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      )}

      <style>{`
        @media (max-width: 900px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>
    </>
  );
}

export default Header;
