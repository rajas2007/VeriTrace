import { Layers } from "lucide-react";
const COLUMNS = [
  {
    heading: "Platform",
    links: ["Approvals", "Approval Roadmap", "Documents", "Tracking"]
  },
  {
    heading: "Explore",
    links: ["Schemes & Incentives", "Government Portals", "Resources", "FAQs"]
  },
  {
    heading: "Support",
    links: ["Help Center", "Contact Support", "Human Assistance"]
  },
  {
    heading: "Legal",
    links: ["Privacy", "Terms", "Accessibility"]
  }
];
function Footer({ onNavigate }) {
  return <footer
    style={{
      background: "#2A3D4A",
      padding: "64px 24px 32px"
    }}
  >
      <div style={{ maxWidth: 1160, margin: "0 auto" }}>
        {
    /* Top row */
  }
        <div
    style={{
      display: "grid",
      gridTemplateColumns: "260px repeat(4, 1fr)",
      gap: 40,
      marginBottom: 56
    }}
    className="footer-grid"
  >
          {
    /* Brand */
  }
          <div>
            <button
    onClick={() => onNavigate(0)}
    style={{
      display: "flex",
      alignItems: "center",
      gap: 9,
      background: "none",
      border: "none",
      cursor: "pointer",
      padding: 0,
      marginBottom: 14
    }}
  >
              <div
    style={{
      width: 30,
      height: 30,
      background: "#5F8699",
      borderRadius: 8,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}
  >
                <Layers size={15} color="#fff" strokeWidth={2} />
              </div>
              <span
    style={{
      fontWeight: 700,
      fontSize: "0.9375rem",
      color: "#fff"
    }}
  >
                UdyogPermit
              </span>
            </button>
            <p
    style={{
      fontSize: "0.875rem",
      color: "rgba(255,255,255,0.55)",
      lineHeight: 1.65,
      margin: 0,
      maxWidth: 220
    }}
  >
              Making industrial compliance simpler, clearer and easier to
              navigate.
            </p>
          </div>

          {
    /* Link columns */
  }
          {COLUMNS.map((col) => <div key={col.heading}>
              <div
    style={{
      fontSize: "0.75rem",
      fontWeight: 700,
      letterSpacing: "0.06em",
      textTransform: "uppercase",
      color: "#fff",
      marginBottom: 16
    }}
  >
                {col.heading}
              </div>
              <ul
    style={{
      listStyle: "none",
      padding: 0,
      margin: 0,
      display: "flex",
      flexDirection: "column",
      gap: 10
    }}
  >
                {col.links.map((link) => <li key={link}>
                    <a
    href="#"
    onClick={(e) => e.preventDefault()}
    style={{
      fontSize: "0.875rem",
      color: "rgba(255,255,255,0.52)",
      textDecoration: "none",
      transition: "color 0.15s"
    }}
    onMouseEnter={(e) => e.target.style.color = "#fff"}
    onMouseLeave={(e) => e.target.style.color = "rgba(255,255,255,0.52)"}
  >
                      {link}
                    </a>
                  </li>)}
              </ul>
            </div>)}
        </div>

        {
    /* Bottom row */
  }
        <div
    style={{
      borderTop: "1px solid rgba(255,255,255,0.1)",
      paddingTop: 24,
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      flexWrap: "wrap",
      gap: 12
    }}
  >
          <span style={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.38)" }}>
            © 2026 UdyogPermit. For informational assistance only.
          </span>
          <div style={{ display: "flex", gap: 20 }}>
            {["Privacy", "Terms", "Accessibility"].map((l) => <a
    key={l}
    href="#"
    onClick={(e) => e.preventDefault()}
    style={{
      fontSize: "0.8125rem",
      color: "rgba(255,255,255,0.38)",
      textDecoration: "none",
      transition: "color 0.15s"
    }}
    onMouseEnter={(e) => e.target.style.color = "rgba(255,255,255,0.8)"}
    onMouseLeave={(e) => e.target.style.color = "rgba(255,255,255,0.38)"}
  >
                {l}
              </a>)}
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .footer-grid { grid-template-columns: 1fr 1fr !important; }
        }
        @media (max-width: 600px) {
          .footer-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </footer>;
}
export {
  Footer as default
};
