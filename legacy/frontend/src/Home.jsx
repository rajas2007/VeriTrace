import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock,
  FileText,
  Building2,
  Zap,
  Shield,
  TrendingUp,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Users,
  LayoutDashboard
} from "lucide-react";
function useParallax(factor = 0.28) {
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const onScroll = () => setOffset(Math.round(window.scrollY * factor));
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [factor]);
  return offset;
}
function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.classList.add("visible");
          obs.disconnect();
        }
      },
      { threshold: 0.12 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}
function HeroLineIllustration() {
  return (
    <svg
      className="hero-illustration-svg"
      xmlns="http://www.w3.org/2000/svg"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
      viewBox="0 0 1400 540"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {
    /* ── LEFT — factory buildings ── */
  }
      <g opacity="0.32" fill="none" stroke="#5F8699" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="18" y="278" width="106" height="175" />
        <path d="M18,278 L71,228 L124,278" />
        <rect x="86" y="196" width="15" height="86" />
        <circle cx="93" cy="190" r="8" fill="#BDD2DB" fillOpacity="0.28" stroke="#5F8699" strokeWidth="1" />
        <circle cx="87" cy="177" r="5.5" fill="#BDD2DB" fillOpacity="0.2" stroke="#5F8699" strokeWidth="0.8" />
        <rect x="30" y="298" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="58" y="298" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="86" y="298" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="30" y="332" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="58" y="332" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="86" y="332" width="17" height="20" fill="#BDD2DB" fillOpacity="0.22" stroke="none" />
        <rect x="52" y="416" width="24" height="37" />
        <rect x="132" y="318" width="65" height="135" />
        <rect x="141" y="330" width="13" height="15" fill="#BDD2DB" fillOpacity="0.2" stroke="none" />
        <rect x="162" y="330" width="13" height="15" fill="#BDD2DB" fillOpacity="0.2" stroke="none" />
        <rect x="141" y="358" width="13" height="15" fill="#BDD2DB" fillOpacity="0.2" stroke="none" />
        <rect x="162" y="358" width="13" height="15" fill="#BDD2DB" fillOpacity="0.2" stroke="none" />
        <line x1="0" y1="453" x2="220" y2="453" />
      </g>

      {
    /* ── LEFT — document reviewer figure ── */
  }
      <g opacity="0.7" fill="none" stroke="#5F8699" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="207" cy="284" r="25" fill="#BDD2DB" fillOpacity="0.2" />
        <path d="M185,276 Q190,256 207,261 Q224,256 229,276" fill="#BDD2DB" fillOpacity="0.32" strokeWidth="1.5" />
        <path d="M188,308 L182,400 L232,400 L226,308 Z" fill="#BDD2DB" fillOpacity="0.16" />
        <path d="M188,308 L207,326 L226,308" />
        <path d="M188,334 Q162,342 150,358" />
        <rect x="126" y="350" width="35" height="46" rx="2" fill="#BDD2DB" fillOpacity="0.28" />
        <path d="M148,350 L161,350 L161,362 L148,362 Z" fill="#BDD2DB" fillOpacity="0.4" stroke="none" />
        <line x1="132" y1="368" x2="155" y2="368" stroke="#5F8699" strokeWidth="1" />
        <line x1="132" y1="377" x2="155" y2="377" stroke="#5F8699" strokeWidth="1" />
        <line x1="132" y1="386" x2="147" y2="386" stroke="#5F8699" strokeWidth="1" />
        <path d="M226,334 Q240,348 244,368" />
        <path d="M190,400 L184,460" />
        <path d="M224,400 L230,460" />
        <path d="M184,460 L170,463" />
        <path d="M230,460 L244,463" />
      </g>

      {
    /* ── Lightbulb above left person ── */
  }
      <g transform="translate(194,228)" opacity="0.62" fill="none" stroke="#5F8699" strokeWidth="1.5">
        <path d="M0,-30 Q26,-52 52,-30" />
        <ellipse cx="24" cy="-15" rx="16" ry="18" fill="#BDD2DB" fillOpacity="0.36" />
        <rect x="17" y="3" width="14" height="5" rx="1" />
        <rect x="18" y="9" width="12" height="5" rx="1" />
        <line x1="24" y1="-34" x2="24" y2="-44" />
        <line x1="5" y1="-26" x2="-2" y2="-32" />
        <line x1="43" y1="-26" x2="50" y2="-32" />
      </g>

      {
    /* Small tree */
  }
      <g transform="translate(168,450)" opacity="0.28" stroke="#5F8699" strokeWidth="1.2" fill="none">
        <rect x="-3" y="0" width="7" height="16" />
        <path d="M-3,0 L-20,-22 L-11,-22 L-23,-44 L-12,-44 L-18,-64 L0,-68 L18,-64 L12,-44 L23,-44 L11,-22 L20,-22 Z" fill="#BDD2DB" fillOpacity="0.28" />
      </g>

      {
    /* ── CENTER — curved workflow path ── */
  }
      <path d="M 272 398 C 332 340, 400 238, 508 196" fill="none" stroke="#5F8699" strokeWidth="1.5" strokeDasharray="7 10" opacity="0.42" />

      {
    /* APPLY node */
  }
      <g transform="translate(534,180)" opacity="0.9">
        <circle cx="0" cy="0" r="42" fill="#BDD2DB" fillOpacity="0.18" stroke="#5F8699" strokeWidth="1.5" />
        <rect x="-15" y="-24" width="30" height="38" rx="2" fill="white" stroke="#5F8699" strokeWidth="1.5" />
        <path d="M9,-24 L15,-24 L15,-18 L9,-18 Z" fill="#BDD2DB" fillOpacity="0.55" stroke="none" />
        <line x1="-10" y1="-14" x2="10" y2="-14" stroke="#5F8699" strokeWidth="1" />
        <line x1="-10" y1="-7" x2="10" y2="-7" stroke="#5F8699" strokeWidth="1" />
        <line x1="-10" y1="0" x2="3" y2="0" stroke="#5F8699" strokeWidth="1" />
        <text x="0" y="60" textAnchor="middle" fontSize="10" fontWeight="700" fill="#5F8699" fontFamily="Inter, sans-serif" letterSpacing="0.06em">APPLY</text>
      </g>

      {
    /* APPLY → APPROVE curve */
  }
      <path d="M 580 146 C 626 108, 706 98, 762 126" fill="none" stroke="#5F8699" strokeWidth="1.5" strokeDasharray="7 10" opacity="0.42" />
      <path d="M 755 122 L 770 128 L 758 138" fill="none" stroke="#5F8699" strokeWidth="1.5" opacity="0.42" />

      {
    /* APPROVE node */
  }
      <g transform="translate(800,162)" opacity="0.9">
        <circle cx="0" cy="0" r="42" fill="#BDD2DB" fillOpacity="0.18" stroke="#5F8699" strokeWidth="1.5" />
        <circle cx="0" cy="0" r="21" fill="white" stroke="#5F8699" strokeWidth="1.5" />
        <path d="M-11,0 L-4,9 L13,-11" fill="none" stroke="#5F8699" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <text x="0" y="60" textAnchor="middle" fontSize="10" fontWeight="700" fill="#5F8699" fontFamily="Inter, sans-serif" letterSpacing="0.06em">APPROVE</text>
      </g>

      {
    /* Decorative birds */
  }
      <g opacity="0.25" stroke="#5F8699" strokeWidth="1.2" fill="none">
        <path d="M 862 112 Q 878 103 894 112" />
        <path d="M 910 92 Q 926 83 942 92" />
        <path d="M 354 200 Q 368 192 382 200" />
      </g>

      {
    /* ── RIGHT — industrial silos ── */
  }
      <g opacity="0.3" fill="none" stroke="#5F8699" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1108" y="265" width="68" height="188" />
        <ellipse cx="1142" cy="265" rx="34" ry="11" />
        <ellipse cx="1142" cy="453" rx="34" ry="11" fill="#BDD2DB" fillOpacity="0.18" />
        <line x1="1168" y1="280" x2="1168" y2="448" />
        <line x1="1160" y1="300" x2="1176" y2="300" />
        <line x1="1160" y1="322" x2="1176" y2="322" />
        <line x1="1160" y1="344" x2="1176" y2="344" />
        <rect x="1186" y="238" width="80" height="215" />
        <ellipse cx="1226" cy="238" rx="40" ry="13" />
        <ellipse cx="1226" cy="453" rx="40" ry="13" fill="#BDD2DB" fillOpacity="0.18" />
        <rect x="1074" y="305" width="50" height="148" />
        <ellipse cx="1099" cy="305" rx="25" ry="9" />
        <ellipse cx="1099" cy="453" rx="25" ry="9" fill="#BDD2DB" fillOpacity="0.14" />
        <line x1="1060" y1="385" x2="1400" y2="385" strokeDasharray="4 6" opacity="0.5" />
        <line x1="1060" y1="453" x2="1400" y2="453" />
      </g>

      {
    /* ── RIGHT — hard-hat figure ── */
  }
      <g opacity="0.7" fill="none" stroke="#5F8699" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M 1285,256 Q 1285,228 1310,224 Q 1335,228 1335,256" fill="#BDD2DB" fillOpacity="0.38" />
        <line x1="1278" y1="256" x2="1342" y2="256" />
        <circle cx="1310" cy="274" r="23" fill="#BDD2DB" fillOpacity="0.18" />
        <path d="M 1292,296 L 1286,385 L 1334,385 L 1328,296 Z" fill="#BDD2DB" fillOpacity="0.15" />
        <line x1="1292" y1="316" x2="1328" y2="316" />
        <line x1="1292" y1="332" x2="1328" y2="332" />
        <path d="M 1292,322 Q 1266,328 1258,344" />
        <rect x="1232" y="336" width="36" height="46" rx="2" fill="#BDD2DB" fillOpacity="0.26" />
        <rect x="1244" y="331" width="12" height="9" rx="1" fill="#BDD2DB" fillOpacity="0.48" />
        <line x1="1238" y1="350" x2="1262" y2="350" stroke="#5F8699" strokeWidth="1" />
        <line x1="1238" y1="360" x2="1262" y2="360" stroke="#5F8699" strokeWidth="1" />
        <line x1="1238" y1="370" x2="1252" y2="370" stroke="#5F8699" strokeWidth="1" />
        <path d="M 1328,322 Q 1352,334 1356,352" />
        <path d="M 1294,385 L 1288,453" />
        <path d="M 1326,385 L 1332,453" />
        <path d="M 1288,453 L 1274,456" />
        <path d="M 1332,453 L 1346,456" />
      </g>

      {
    /* BUILD GROW CONTRIBUTE sign */
  }
      <g transform="translate(1360,286)" opacity="0.5">
        <rect width="88" height="74" rx="4" fill="#BDD2DB" fillOpacity="0.12" stroke="#5F8699" strokeWidth="1.2" />
        <text x="44" y="22" textAnchor="middle" fontSize="9" fontWeight="700" fill="#5F8699" fontFamily="Inter, sans-serif" letterSpacing="0.05em">BUILD</text>
        <text x="44" y="40" textAnchor="middle" fontSize="9" fontWeight="700" fill="#5F8699" fontFamily="Inter, sans-serif" letterSpacing="0.05em">GROW</text>
        <text x="44" y="58" textAnchor="middle" fontSize="8" fontWeight="700" fill="#5F8699" fontFamily="Inter, sans-serif" letterSpacing="0.04em">CONTRIBUTE</text>
        <line x1="44" y1="74" x2="44" y2="100" stroke="#5F8699" strokeWidth="1.5" />
      </g>

      {
    /* Right edge decorative arrow */
  }
      <g opacity="0.22" stroke="#5F8699" strokeWidth="1.2" fill="none">
        <path d="M 1360 210 Q 1390 196 1405 212" />
        <path d="M 1397 208 L 1406 212 L 1398 218" />
      </g>
    </svg>
  );
  }
  function BgNodes() {
  return <svg xmlns="http://www.w3.org/2000/svg" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 0 }} viewBox="0 0 1200 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g opacity="0.08">
        <circle cx="740" cy="90" r="9" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="840" cy="170" r="6" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1" />
        <circle cx="940" cy="115" r="9" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="1020" cy="215" r="6" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1" />
        <circle cx="895" cy="295" r="9" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="988" cy="362" r="6" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1" />
        <circle cx="772" cy="328" r="6" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1" />
        <circle cx="1062" cy="302" r="9" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <line x1="740" y1="90" x2="840" y2="170" stroke="#5F8699" strokeWidth="1" />
        <line x1="840" y1="170" x2="940" y2="115" stroke="#5F8699" strokeWidth="1" />
        <line x1="940" y1="115" x2="1020" y2="215" stroke="#5F8699" strokeWidth="1" />
        <line x1="1020" y1="215" x2="895" y2="295" stroke="#5F8699" strokeWidth="1" />
        <line x1="895" y1="295" x2="988" y2="362" stroke="#5F8699" strokeWidth="1" />
        <line x1="895" y1="295" x2="772" y2="328" stroke="#5F8699" strokeWidth="1" />
        <line x1="1020" y1="215" x2="1062" y2="302" stroke="#5F8699" strokeWidth="1" />
        <line x1="840" y1="170" x2="772" y2="328" stroke="#5F8699" strokeWidth="0.8" strokeDasharray="3 5" />
        <circle cx="900" cy="200" r="190" fill="none" stroke="#BDD2DB" strokeWidth="1" strokeDasharray="4 8" />
      </g>
    </svg>;
}
function BgDocuments() {
  return <svg xmlns="http://www.w3.org/2000/svg" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 0 }} viewBox="0 0 1200 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g opacity="0.065">
        <g fill="#BDD2DB" fillOpacity="0.25" stroke="#2A3D4A" strokeWidth="1">
          <rect x="72" y="90" width="72" height="90" rx="3" />
          <path d="M126,90 L144,108 L126,108 Z" fill="#BDD2DB" fillOpacity="0.4" />
          <line x1="84" y1="118" x2="132" y2="118" stroke="#2A3D4A" strokeWidth="0.7" />
          <line x1="84" y1="130" x2="132" y2="130" stroke="#2A3D4A" strokeWidth="0.7" />
          <line x1="84" y1="142" x2="118" y2="142" stroke="#2A3D4A" strokeWidth="0.7" />
          <line x1="84" y1="154" x2="124" y2="154" stroke="#2A3D4A" strokeWidth="0.7" />
        </g>
        <g fill="#BDD2DB" fillOpacity="0.18" stroke="#2A3D4A" strokeWidth="0.9" transform="translate(110,50) rotate(7)">
          <rect width="64" height="80" rx="3" />
          <path d="M46,0 L64,18 L46,18 Z" fill="#BDD2DB" fillOpacity="0.35" />
          <line x1="10" y1="28" x2="54" y2="28" stroke="#2A3D4A" strokeWidth="0.7" />
          <line x1="10" y1="40" x2="54" y2="40" stroke="#2A3D4A" strokeWidth="0.7" />
          <line x1="10" y1="52" x2="42" y2="52" stroke="#2A3D4A" strokeWidth="0.7" />
        </g>
        <g fill="#BDD2DB" fillOpacity="0.12" stroke="#2A3D4A" strokeWidth="0.8" transform="translate(60,210) rotate(-4)">
          <rect width="60" height="76" rx="3" />
          <path d="M42,0 L60,18 L42,18 Z" fill="#BDD2DB" fillOpacity="0.28" />
          <line x1="10" y1="26" x2="50" y2="26" stroke="#2A3D4A" strokeWidth="0.6" />
          <line x1="10" y1="37" x2="50" y2="37" stroke="#2A3D4A" strokeWidth="0.6" />
          <line x1="10" y1="48" x2="38" y2="48" stroke="#2A3D4A" strokeWidth="0.6" />
        </g>
        <path d="M210,195 L222,210 L246,180" fill="none" stroke="#5F8699" strokeWidth="2" strokeLinecap="round" />
        <path d="M174,355 L184,368 L204,342" fill="none" stroke="#5F8699" strokeWidth="2" strokeLinecap="round" />
      </g>
    </svg>;
}
function BgJourneyLine() {
  return <svg xmlns="http://www.w3.org/2000/svg" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 0 }} viewBox="0 0 1200 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g opacity="0.075">
        <path d="M 0 400 C 120 375, 240 440, 400 380 S 600 300, 760 345 S 960 405, 1120 330 S 1280 295, 1400 310" fill="none" stroke="#5F8699" strokeWidth="2" strokeDasharray="8 12" />
        <circle cx="200" cy="392" r="7" fill="#5F8699" fillOpacity="0.45" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="440" cy="365" r="7" fill="#5F8699" fillOpacity="0.45" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="680" cy="338" r="9" fill="#5F8699" fillOpacity="0.6" stroke="#5F8699" strokeWidth="1.6" />
        <circle cx="920" cy="368" r="7" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <circle cx="1100" cy="332" r="7" fill="#BDD2DB" stroke="#5F8699" strokeWidth="1.2" />
        <line x1="200" y1="392" x2="200" y2="425" stroke="#5F8699" strokeWidth="1" strokeDasharray="2 3" />
        <line x1="440" y1="365" x2="440" y2="398" stroke="#5F8699" strokeWidth="1" strokeDasharray="2 3" />
        <line x1="680" y1="338" x2="680" y2="371" stroke="#5F8699" strokeWidth="1" strokeDasharray="2 3" />
      </g>
    </svg>;
}
function BgGrowth() {
  return <svg xmlns="http://www.w3.org/2000/svg" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", zIndex: 0 }} viewBox="0 0 1200 480" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g opacity="0.072">
        <rect x="820" y="270" width="38" height="150" rx="3" fill="#BDD2DB" />
        <rect x="872" y="210" width="38" height="210" rx="3" fill="#BDD2DB" />
        <rect x="924" y="155" width="38" height="265" rx="3" fill="#BDD2DB" />
        <rect x="976" y="195" width="38" height="225" rx="3" fill="#BDD2DB" />
        <rect x="1028" y="115" width="38" height="305" rx="3" fill="#BDD2DB" />
        <rect x="1080" y="95" width="38" height="325" rx="3" fill="#BDD2DB" />
        <line x1="800" y1="420" x2="1160" y2="420" stroke="#2A3D4A" strokeWidth="1" />
        <path d="M 820 270 C 872 218, 924 162, 976 200 S 1028 122, 1090 100" fill="none" stroke="#5F8699" strokeWidth="1.8" strokeDasharray="4 5" />
        <circle cx="820" cy="270" r="4" fill="#5F8699" fillOpacity="0.55" />
        <circle cx="924" cy="158" r="4" fill="#5F8699" fillOpacity="0.55" />
        <circle cx="1028" cy="120" r="4" fill="#5F8699" fillOpacity="0.55" />
        <circle cx="1090" cy="100" r="4" fill="#5F8699" fillOpacity="0.55" />
        <path d="M1108,78 L1130,56 L1152,78" fill="none" stroke="#5F8699" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="1130" y1="56" x2="1130" y2="98" stroke="#5F8699" strokeWidth="1.5" strokeLinecap="round" />
      </g>
    </svg>;
}
function ApprovalRow({
  label,
  done,
  progress
}) {
  return <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0" }}>
      <div style={{ flexShrink: 0 }}>
        {done ? <CheckCircle2 size={16} color="#5F8699" strokeWidth={2.5} /> : progress ? <div
    style={{
      width: 16,
      height: 16,
      borderRadius: "50%",
      background: "#E8F1F4",
      border: "2px solid #5F8699",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}
  >
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#5F8699" }} />
          </div> : <Circle size={16} color="#BDD2DB" strokeWidth={2} />}
      </div>
      <span
    style={{
      fontSize: "0.8125rem",
      color: done ? "#8BA3AE" : progress ? "#2A3D4A" : "#BDD2DB",
      fontWeight: progress ? 500 : 400,
      flex: 1
    }}
  >
        {label}
      </span>
      {progress && <span
    style={{
      fontSize: "0.625rem",
      fontWeight: 700,
      padding: "2px 7px",
      borderRadius: 99,
      background: "#E8F1F4",
      color: "#5F8699",
      border: "1px solid #BDD2DB"
    }}
  >
          In Progress
        </span>}
    </div>;
}
function DocRow({ label, done }) {
  return <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "6px 0",
      borderBottom: "1px solid #EAE4DA"
    }}
  >
      {done ? <CheckCircle2
    size={14}
    color="#5F8699"
    strokeWidth={2.5}
    style={{ flexShrink: 0 }}
  /> : <Circle size={14} color="#BDD2DB" strokeWidth={2} style={{ flexShrink: 0 }} />}
      <span style={{ fontSize: "0.8125rem", color: done ? "#8BA3AE" : "#2A3D4A" }}>
        {label}
      </span>
    </div>;
}
function RoadmapMockup() {
  return <div
    style={{
      background: "#fff",
      border: "1.5px solid #CDDDE3",
      borderRadius: 16,
      boxShadow: "0 24px 64px rgba(42,61,74,0.12), 0 4px 16px rgba(42,61,74,0.06)",
      overflow: "hidden",
      width: "100%",
      maxWidth: 480,
      position: "relative"
    }}
  >
      {
    /* Window chrome */
  }
      <div
    style={{
      background: "#fff",
      borderBottom: "1px solid #E0EBF0",
      padding: "10px 16px",
      display: "flex",
      alignItems: "center",
      gap: 6
    }}
  >
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FCA5A5" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FDE68A" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#BBF7D0" }} />
        <span style={{ marginLeft: 10, fontSize: "0.75rem", color: "#8BA3AE", fontWeight: 500 }}>
          Approval Roadmap — Manufacturing Unit
        </span>
      </div>

      {
    /* Header strip */
  }
      <div
    style={{
      padding: "16px 20px",
      borderBottom: "1px solid #EAE4DA",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center"
    }}
  >
        <div>
          <div style={{ fontWeight: 700, fontSize: "0.9375rem", color: "#2A3D4A" }}>
            Manufacturing Unit
          </div>
          <div
    style={{
      fontSize: "0.75rem",
      color: "#8BA3AE",
      display: "flex",
      gap: 10,
      marginTop: 2
    }}
  >
            <span>📍 Maharashtra</span>
            <span>·</span>
            <span>Project Stage: Setup</span>
          </div>
        </div>
        <span
    style={{
      fontSize: "0.6875rem",
      fontWeight: 700,
      padding: "3px 10px",
      borderRadius: 99,
      background: "#E8F1F4",
      color: "#5F8699",
      border: "1px solid #BDD2DB"
    }}
  >
          Active
        </span>
      </div>

      {
    /* Progress bar */
  }
      <div
    style={{
      padding: "12px 20px",
      background: "#E8F1F4",
      borderBottom: "1px solid #D5E8ED"
    }}
  >
        <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: 8
    }}
  >
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#2A3D4A" }}>
            Overall Progress
          </span>
          <span style={{ fontSize: "0.75rem", color: "#8BA3AE" }}>7 of 18 approvals</span>
        </div>
        <div
    style={{
      height: 6,
      background: "#BDD2DB",
      borderRadius: 99,
      overflow: "hidden"
    }}
  >
          <div
    style={{
      height: "100%",
      width: "39%",
      background: "#5F8699",
      borderRadius: 99,
      transition: "width 1s ease"
    }}
  />
        </div>
      </div>

      {
    /* Approvals list */
  }
      <div style={{ padding: "4px 20px 8px" }}>
        <div
    style={{
      fontSize: "0.6875rem",
      fontWeight: 700,
      letterSpacing: "0.06em",
      textTransform: "uppercase",
      color: "#8BA3AE",
      padding: "10px 0 4px"
    }}
  >
          Approvals
        </div>
        <ApprovalRow label="Business Registration" done />
        <ApprovalRow label="Land & Building Approval" done />
        <ApprovalRow label="Pollution Control NOC" progress />
        <ApprovalRow label="Factory License" />
        <ApprovalRow label="Fire NOC" />
      </div>

      {
    /* Footer row */
  }
      <div
    style={{
      padding: "10px 20px",
      borderTop: "1px solid #E0EBF0",
      background: "#fff",
      display: "flex",
      gap: 16
    }}
  >
        <div style={{ fontSize: "0.75rem", color: "#8BA3AE" }}>
          <span style={{ fontWeight: 600, color: "#2A3D4A" }}>12</span> Documents
        </div>
        <div style={{ fontSize: "0.75rem", color: "#8BA3AE" }}>
          <span style={{ fontWeight: 600, color: "#2A3D4A" }}>6</span> Incentives
        </div>
        <div
    style={{
      fontSize: "0.75rem",
      color: "#8BA3AE",
      marginLeft: "auto",
      display: "flex",
      alignItems: "center",
      gap: 4
    }}
  >
          <Clock size={11} />
          Next: 14 Sept
        </div>
      </div>
    </div>;
}
function KnowApprovalsMockup() {
  return <div style={{ position: "relative", padding: "28px 32px 20px 16px", display: "inline-block" }}>
      <div className="feat-chip" style={{ position: "absolute", top: 2, left: 28, animationDelay: "0s" }}>
        <CheckCircle2 size={11} color="#5F8699" />
        18 Approvals
      </div>
      <div className="feat-chip" style={{ position: "absolute", top: 88, right: 0, animationDelay: "0.55s" }}>
        <FileText size={11} color="#5F8699" />
        12 Documents
      </div>
      <div className="feat-chip" style={{ position: "absolute", bottom: 72, right: 0, animationDelay: "1.1s" }}>
        <Zap size={11} color="#5F8699" />
        6 Incentives
      </div>
      <div className="card" style={{ padding: 22, maxWidth: 490 }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#8BA3AE", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 14 }}>
          Project Details
        </div>
        {[
    { label: "Industry", value: "Manufacturing \u2014 Garment" },
    { label: "Location", value: "Pune, Maharashtra" },
    { label: "Investment", value: "\u20B950 Lakh \u2013 \u20B92 Crore" },
    { label: "Stage", value: "New Setup" }
  ].map((r) => <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid #EAE4DA" }}>
            <span style={{ fontSize: "0.8125rem", color: "#8BA3AE" }}>{r.label}</span>
            <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "#2A3D4A" }}>{r.value}</span>
          </div>)}
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px dashed #D5C9B8" }}>
          <div style={{ fontSize: "0.6875rem", fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#8BA3AE", marginBottom: 10 }}>
            Applicable Approvals
          </div>
          {[
    { label: "Business Registration", done: true },
    { label: "Factory License", progress: true },
    { label: "Pollution Control NOC", pending: true }
  ].map((a) => <div key={a.label} style={{ display: "flex", alignItems: "center", gap: 9, padding: "6px 0" }}>
              <div style={{ flexShrink: 0 }}>
                {a.done ? <CheckCircle2 size={14} color="#5F8699" strokeWidth={2.5} /> : a.progress ? <div style={{ width: 14, height: 14, borderRadius: "50%", background: "#E8F1F4", border: "2px solid #5F8699", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: 4, height: 4, borderRadius: "50%", background: "#5F8699" }} />
                  </div> : <Circle size={14} color="#BDD2DB" strokeWidth={2} />}
              </div>
              <span style={{ fontSize: "0.8125rem", color: a.done ? "#8BA3AE" : a.progress ? "#2A3D4A" : "#8BA3AE", flex: 1, fontWeight: a.progress ? 500 : 400 }}>
                {a.label}
              </span>
              {a.progress && <span style={{ fontSize: "0.5625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 99, background: "#E8F1F4", color: "#5F8699", border: "1px solid #BDD2DB" }}>
                  Active
                </span>}
            </div>)}
        </div>
        <div style={{ marginTop: 14, padding: "12px 16px", background: "#E8F1F4", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: "1.25rem", color: "#5F8699" }}>18</div>
            <div style={{ fontSize: "0.75rem", color: "#5F8699", opacity: 0.8 }}>approvals applicable</div>
          </div>
          <ArrowRight size={18} color="#5F8699" />
        </div>
      </div>
    </div>;
}
function PrepareDocsMockup() {
  return <div style={{ position: "relative", maxWidth: 460 }}>
      <div style={{ position: "absolute", top: 10, left: 10, right: -10, bottom: -10, background: "#EEF4F6", borderRadius: 14, border: "1.5px solid #C8DADE" }} />
      <div style={{ position: "absolute", top: 5, left: 5, right: -5, bottom: -5, background: "#F4F8FA", borderRadius: 13, border: "1.5px solid #D5E8ED" }} />
      <div className="card" style={{ padding: 22, position: "relative", zIndex: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "#2A3D4A" }}>Required Documents</span>
          <span style={{ fontSize: "0.6875rem", fontWeight: 700, padding: "3px 8px", borderRadius: 99, background: "var(--success-light)", color: "#059669" }}>3 / 5 ready</span>
        </div>
        <div style={{ height: 4, background: "#D5C9B8", borderRadius: 99, marginBottom: 16, overflow: "hidden" }}>
          <div style={{ height: "100%", width: "60%", background: "#5F8699", borderRadius: 99 }} />
        </div>
        <DocRow label="Land ownership document" done />
        <DocRow label="Project report" done />
        <DocRow label="Identity proof" done />
        <DocRow label="Pollution assessment" />
        <DocRow label="Building plan" />
        <div style={{ marginTop: 14 }}>
          <button className="btn btn-secondary" style={{ width: "100%", justifyContent: "center", fontSize: "0.8125rem" }}>
            View all documents
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>;
}
function TrackMockup() {
  const stages = [
    { label: "Business Registration", status: "done", date: "Mar 2024", detail: "MCA + state registration complete" },
    { label: "Land & Building Approval", status: "done", date: "Apr 2024", detail: "Municipal plan approved" },
    { label: "Pollution Control NOC", status: "progress", date: "May 2024", detail: "Application submitted \u2014 under review" },
    { label: "Factory License", status: "upcoming", date: "Jun 2024", detail: "Awaiting NOC clearance" },
    { label: "Fire Safety Certificate", status: "upcoming", date: "Jul 2024", detail: "Post-license step" }
  ];
  return <div className="card" style={{ padding: "22px 26px", maxWidth: 470 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <span style={{ fontWeight: 600, fontSize: "0.9375rem", color: "#2A3D4A" }}>Approval Timeline</span>
        <span style={{ fontSize: "0.6875rem", fontWeight: 700, padding: "3px 10px", borderRadius: 99, background: "#E8F1F4", color: "#5F8699", border: "1px solid #BDD2DB" }}>
          2 of 5 complete
        </span>
      </div>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {stages.map((s, i) => <div key={s.label} style={{ display: "flex", gap: 14, paddingBottom: i < stages.length - 1 ? 22 : 0, position: "relative" }}>
            {i < stages.length - 1 && <div style={{ position: "absolute", left: 13, top: 28, width: 2, bottom: 0, background: s.status === "done" ? "#5F8699" : "#D5C9B8" }} />}
            <div style={{ width: 28, height: 28, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: s.status === "done" ? "#5F8699" : s.status === "progress" ? "#5F8699" : "#EEF4F6", border: s.status === "upcoming" ? "2px solid #D5C9B8" : "none", zIndex: 1 }}>
              {s.status === "done" ? <CheckCircle2 size={13} color="#fff" strokeWidth={2.5} /> : s.status === "progress" ? <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#fff" }} /> : <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#BDD2DB" }} />}
            </div>
            <div style={{ paddingTop: 2, flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: s.status === "progress" ? 600 : 400, color: s.status === "upcoming" ? "#8BA3AE" : "#2A3D4A", lineHeight: 1.3 }}>
                  {s.label}
                </span>
                <span style={{ fontSize: "0.6875rem", color: "#8BA3AE", flexShrink: 0 }}>{s.date}</span>
              </div>
              <div style={{ fontSize: "0.75rem", color: s.status === "done" ? "#5F8699" : s.status === "progress" ? "#5F8699" : "#8BA3AE", marginTop: 2 }}>
                {s.detail}
              </div>
            </div>
          </div>)}
      </div>
    </div>;
}
function IncentivesMockup() {
  return <div style={{ position: "relative", maxWidth: 470 }}>
      <div style={{ position: "absolute", top: 10, left: 10, right: -10, bottom: -10, background: "#EEF4F6", borderRadius: 14, border: "1.5px solid #C8DADE" }} />
      <div style={{ position: "absolute", top: 5, left: 5, right: -5, bottom: -5, background: "#F4F8FA", borderRadius: 13, border: "1.5px solid #D5E8ED" }} />
      <div className="card" style={{ padding: 22, position: "relative", zIndex: 2 }}>
        <div style={{ fontWeight: 600, fontSize: "0.9375rem", color: "#2A3D4A", marginBottom: 4 }}>Schemes & Incentives</div>
        <div style={{ fontSize: "0.8125rem", color: "#8BA3AE", marginBottom: 16 }}>6 schemes found for your project</div>
        {[
    { name: "Manufacturing Incentive Scheme", tag: "Capital Support", amount: "Up to \u20B940L", eligible: true },
    { name: "MSME Technology Upgradation", tag: "Equipment Subsidy", amount: "35% subsidy", eligible: true },
    { name: "Employment Generation Scheme", tag: "Wage Assistance", amount: "\u20B95K / employee", eligible: false },
    { name: "Green Energy Transition Fund", tag: "Environmental", amount: "Up to \u20B920L", eligible: true }
  ].map((s, i) => <div key={s.name} style={{ padding: "11px 14px", marginBottom: i < 3 ? 8 : 0, display: "flex", justifyContent: "space-between", alignItems: "flex-start", border: "1.5px solid #DCE9EF", borderRadius: 10, background: "#fff" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 500, fontSize: "0.8125rem", color: "#2A3D4A", marginBottom: 4, lineHeight: 1.3 }}>{s.name}</div>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ fontSize: "0.625rem", fontWeight: 600, padding: "2px 7px", borderRadius: 99, background: "#F6EFE2", color: "#8BA3AE" }}>Maharashtra</span>
                <span style={{ fontSize: "0.625rem", fontWeight: 600, padding: "2px 7px", borderRadius: 99, background: "#F6EFE2", color: "#8BA3AE" }}>{s.tag}</span>
                <span style={{ fontSize: "0.625rem", fontWeight: 600, color: "#5F8699" }}>{s.amount}</span>
              </div>
            </div>
            {s.eligible ? <span style={{ fontSize: "0.5625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 99, background: "var(--success-light)", color: "#059669", flexShrink: 0, marginLeft: 8 }}>Eligible</span> : <span style={{ fontSize: "0.5625rem", fontWeight: 700, padding: "2px 7px", borderRadius: 99, background: "#F6F6F6", color: "#8BA3AE", border: "1px solid #E0E0E0", flexShrink: 0, marginLeft: 8 }}>Check</span>}
          </div>)}
      </div>
    </div>;
}
const CAROUSEL_SLIDES = [
  {
    url: "https://images.unsplash.com/photo-1742280923779-bde44046c5d2?w=680&q=80&fit=crop&crop=center",
    label: "Textile Manufacturing",
    desc: "Skilled workers on garment production lines"
  },
  {
    url: "https://images.unsplash.com/photo-1764114908655-9a26d32750a0?w=680&q=80&fit=crop&crop=center",
    label: "Heavy Industry",
    desc: "Industrial machinery at work in modern factories"
  },
  {
    url: "https://images.unsplash.com/photo-1748944079305-8d2a86e7ad32?w=680&q=80&fit=crop&crop=center",
    label: "Production Oversight",
    desc: "Factory teams managing high-throughput operations"
  },
  {
    url: "https://images.unsplash.com/photo-1741275273537-e172e1411b3a?w=680&q=80&fit=crop&crop=center",
    label: "Manufacturing Operations",
    desc: "Precision manufacturing in industrial facilities"
  },
  {
    url: "https://images.unsplash.com/photo-1771244688590-1e481dba1b5a?w=680&q=80&fit=crop&crop=center",
    label: "Business Leadership",
    desc: "Entrepreneurs navigating compliance and growth"
  },
  {
    url: "https://images.unsplash.com/photo-1770626894265-bdb99db109f1?w=680&q=80&fit=crop&crop=center",
    label: "Documentation & Compliance",
    desc: "Professionals managing regulatory requirements"
  }
];
function ImageCarousel() {
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);
  const containerRef = useRef(null);
  const CARD_W = 340;
  const GAP = 20;
  const STEP = CARD_W + GAP;
  const scroll = (dir) => {
    containerRef.current?.scrollBy({ left: dir * STEP, behavior: "smooth" });
  };
  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    setAtStart(el.scrollLeft <= 4);
    setAtEnd(el.scrollLeft >= el.scrollWidth - el.clientWidth - 4);
  };
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);
  const arrowStyle = (disabled) => ({
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: disabled ? "#EEF4F6" : "#fff",
    border: "1.5px solid #BDD2DB",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.42 : 1,
    transition: "all 0.15s ease",
    flexShrink: 0
  });
  return <div>
      <div
    ref={containerRef}
    className="carousel-track"
    style={{
      display: "flex",
      gap: GAP,
      overflowX: "auto",
      scrollSnapType: "x mandatory",
      paddingBottom: 4
    }}
  >
        {CAROUSEL_SLIDES.map((s, i) => <div
    key={i}
    className="carousel-card"
    style={{
      flexShrink: 0,
      width: CARD_W,
      scrollSnapAlign: "start",
      background: "#fff",
      borderRadius: 14,
      border: "1.5px solid #D9E5EB",
      overflow: "hidden",
      boxShadow: "0 4px 20px rgba(42,61,74,0.07), 0 1px 4px rgba(42,61,74,0.04)",
      transition: "transform 0.22s ease, box-shadow 0.22s ease"
    }}
  >
            <div
    style={{
      width: "100%",
      height: 210,
      overflow: "hidden",
      background: "#EEF4F6"
    }}
  >
              <img
    src={s.url}
    alt={s.label}
    style={{
      width: "100%",
      height: "100%",
      objectFit: "cover",
      display: "block",
      transition: "transform 0.4s ease"
    }}
    loading="lazy"
  />
            </div>
            <div style={{ padding: "16px 18px" }}>
              <div
    style={{
      fontWeight: 600,
      fontSize: "0.875rem",
      color: "#2A3D4A",
      marginBottom: 4
    }}
  >
                {s.label}
              </div>
              <p
    style={{
      fontSize: "0.8125rem",
      color: "#8BA3AE",
      margin: 0,
      lineHeight: 1.5
    }}
  >
                {s.desc}
              </p>
            </div>
          </div>)}
      </div>

      {
    /* Controls */
  }
      <div
    style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 14,
      marginTop: 28
    }}
  >
        <button
    onClick={() => scroll(-1)}
    disabled={atStart}
    style={arrowStyle(atStart)}
    aria-label="Previous"
  >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
    d="M10 12L6 8L10 4"
    stroke="#5F8699"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
  />
          </svg>
        </button>

        <button
    onClick={() => scroll(1)}
    disabled={atEnd}
    style={arrowStyle(atEnd)}
    aria-label="Next"
  >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
    d="M6 4L10 8L6 12"
    stroke="#5F8699"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
  />
          </svg>
        </button>
      </div>
    </div>;
}
function RevealSection({
  children,
  style
}) {
  const ref = useReveal();
  return <div ref={ref} className="reveal" style={style}>
      {children}
    </div>;
}
const tealBtn = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  background: "#5F8699",
  color: "#fff",
  fontSize: "0.9375rem",
  fontWeight: 600,
  padding: "13px 26px",
  borderRadius: 10,
  border: "1.5px solid #5F8699",
  cursor: "pointer",
  boxShadow: "0 2px 10px rgba(95,134,153,0.28)",
  transition: "background 0.18s ease, box-shadow 0.18s ease, transform 0.12s ease",
  whiteSpace: "nowrap",
  textDecoration: "none"
};
const outlineBtn = {
  display: "inline-flex",
  alignItems: "center",
  gap: 8,
  background: "#fff",
  color: "#2A3D4A",
  fontSize: "0.9375rem",
  fontWeight: 600,
  padding: "13px 26px",
  borderRadius: 10,
  border: "1.5px solid #BDD2DB",
  cursor: "pointer",
  transition: "background 0.18s ease, border-color 0.18s ease, transform 0.12s ease",
  whiteSpace: "nowrap",
  textDecoration: "none"
};
function Home({ onStart }) {
  return <div style={{ background: "#F6EFE2" }}>

      {
    /* ── HERO — line-art illustration background ──────── */
  }
      <div style={{ padding: "20px 24px 0" }}>
        <div
    style={{
      position: "relative",
      overflow: "hidden",
      background: "#fff",
      borderRadius: 16,
      boxShadow: "0 2px 24px rgba(42,61,74,0.07), 0 1px 4px rgba(42,61,74,0.04)"
    }}
  >
          <HeroLineIllustration />
          <div style={{ position: "relative", zIndex: 1, maxWidth: 1160, margin: "0 auto" }}>

          <section
    style={{
      padding: "80px 64px",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: "64px",
      alignItems: "center",
      position: "relative",
      zIndex: 1
    }}
    className="hero-grid"
  >
            {
    /* Left copy */
  }
            <div className="fade-up">
              {
    /* Label */
  }
              <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      background: "#E8F1F4",
      color: "#5F8699",
      fontSize: "0.6875rem",
      fontWeight: 700,
      letterSpacing: "0.08em",
      textTransform: "uppercase",
      padding: "5px 12px",
      borderRadius: 99,
      border: "1px solid #BDD2DB",
      marginBottom: 24
    }}
  >
                <Sparkles size={11} />
                AI-powered industrial compliance
              </div>

              <h1
    style={{
      fontSize: "clamp(2.5rem, 4.5vw, 3.5rem)",
      fontWeight: 800,
      lineHeight: 1.06,
      letterSpacing: "-0.03em",
      color: "#2A3D4A",
      marginBottom: 16
    }}
  >
                Udyog
                <br />
                <span style={{ color: "#5F8699" }}>Permit</span> AI
              </h1>

              <p
    style={{
      fontSize: "1.125rem",
      fontWeight: 600,
      color: "#2A3D4A",
      lineHeight: 1.4,
      marginBottom: 12,
      letterSpacing: "-0.01em"
    }}
  >
                Simplifying business approvals with AI.
              </p>

              <p
    style={{
      fontSize: "1rem",
      color: "#5F8699",
      lineHeight: 1.7,
      marginBottom: 36,
      maxWidth: 440
    }}
  >
                Discover the approvals, documents, incentives and government
                requirements that apply to your industrial project — all in one
                place.
              </p>

              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button
    style={tealBtn}
    onClick={onStart}
    className="hero-cta-primary"
  >
                  Get My Approval Roadmap
                  <ArrowRight size={16} />
                </button>
                <button
    style={outlineBtn}
    onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}
    className="hero-cta-secondary"
  >
                  Explore Approvals
                </button>
              </div>

              {
    /* Supporting badges */
  }
              <div style={{ display: "flex", gap: 10, marginTop: 36, flexWrap: "wrap" }}>
                {[
    { icon: <FileText size={13} />, text: "Documents Checklist" },
    { icon: <Zap size={13} />, text: "Eligible Subsidies" },
    { icon: <Sparkles size={13} />, text: "Real-time AI Guidance" }
  ].map((chip) => <div
    key={chip.text}
    style={{
      display: "flex",
      alignItems: "center",
      gap: 6,
      background: "#fff",
      border: "1.5px solid #BDD2DB",
      borderRadius: 99,
      padding: "6px 13px",
      fontSize: "0.8125rem",
      color: "#2A3D4A",
      fontWeight: 500,
      boxShadow: "0 1px 4px rgba(42,61,74,0.06)"
    }}
  >
                    <span style={{ color: "#5F8699" }}>{chip.icon}</span>
                    {chip.text}
                  </div>)}
              </div>
            </div>

            {
    /* Right product mockup */
  }
            <div
    style={{ display: "flex", justifyContent: "center", position: "relative" }}
    className="fade-up hero-mockup"
  >
              <div className="float">
                <RoadmapMockup />
              </div>
            </div>
          </section>
          </div>
        </div>
      </div>

      {
    /* ── BUILT FOR REAL BUSINESSES — image carousel ─────── */
  }
      <section style={{ padding: "72px 24px 64px", background: "#F6EFE2" }}>
        <div style={{ maxWidth: 1160, margin: "0 auto" }}>
          <RevealSection>
            <div style={{ textAlign: "center", marginBottom: 44 }}>
              <h2
    style={{
      fontSize: "clamp(1.625rem, 2.8vw, 2.25rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 12
    }}
  >
                Built for Real Businesses
              </h2>
              <p
    style={{
      fontSize: "1rem",
      color: "#5F8699",
      maxWidth: 480,
      margin: "0 auto",
      lineHeight: 1.65
    }}
  >
                Helping businesses navigate approvals, compliance, and
                opportunities at every stage.
              </p>
            </div>
            <ImageCarousel />
          </RevealSection>
        </div>
      </section>

      {
    /* ── TRUST BAND ─────────────────────────────────────── */
  }
      <section
    style={{
      borderTop: "1px solid #D5C9B8",
      borderBottom: "1px solid #D5C9B8",
      background: "#fff",
      padding: "28px 24px"
    }}
  >
        <RevealSection>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <p
    style={{
      textAlign: "center",
      fontSize: "0.875rem",
      fontWeight: 600,
      color: "#8BA3AE",
      letterSpacing: "0.04em",
      textTransform: "uppercase",
      marginBottom: 24
    }}
  >
              Everything you need to navigate industrial compliance.
            </p>
            <div style={{ display: "flex", justifyContent: "center", gap: 0, flexWrap: "wrap" }}>
              {[
    { icon: <Shield size={18} />, label: "Government Approvals" },
    { icon: <TrendingUp size={18} />, label: "Industrial Schemes" },
    { icon: <FileText size={18} />, label: "Document Guidance" },
    { icon: <LayoutDashboard size={18} />, label: "Application Tracking" },
    { icon: <Users size={18} />, label: "Expert Assistance" }
  ].map((item, i) => <div
    key={item.label}
    style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "10px 28px",
      borderRight: i < 4 ? "1px solid #D5C9B8" : "none",
      color: "#2A3D4A",
      fontSize: "0.875rem",
      fontWeight: 500
    }}
  >
                  <span style={{ color: "#5F8699" }}>{item.icon}</span>
                  {item.label}
                </div>)}
            </div>
          </div>
        </RevealSection>
      </section>

      {
    /* ── FEATURES ───────────────────────────────────────── */
  }
      <div id="features">
        {
    /* Heading */
  }
        <section style={{ padding: "80px 24px 52px", background: "#fff" }}>
          <div style={{ maxWidth: 1160, margin: "0 auto" }}>
            <RevealSection>
              <div style={{ textAlign: "center" }}>
                <h2 style={{ fontSize: "clamp(1.75rem, 3vw, 2.5rem)", fontWeight: 800, letterSpacing: "-0.02em", color: "#2A3D4A", marginBottom: 14 }}>
                  From your project idea to operation.
                </h2>
                <p style={{ fontSize: "1.0625rem", color: "#5F8699", maxWidth: 500, margin: "0 auto", lineHeight: 1.65 }}>
                  One place to understand what applies, prepare what you need, and keep moving.
                </p>
              </div>
            </RevealSection>
          </div>
        </section>

        {
    /* 01 — Know Your Approvals — beige */
  }
        <section style={{ padding: "72px 24px", background: "#F6EFE2", position: "relative", overflow: "hidden" }}>
          <BgNodes />
          <div style={{ maxWidth: 1160, margin: "0 auto", position: "relative", zIndex: 1 }}>
            <RevealSection>
              <div className="feature-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#5F8699", letterSpacing: "0.06em", textTransform: "uppercase", display: "block", marginBottom: 14 }}>01 — Know Your Approvals</span>
                  <h3 style={{ fontSize: "clamp(1.375rem, 2.5vw, 1.875rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#2A3D4A", lineHeight: 1.2, marginBottom: 16 }}>See exactly what applies to your project.</h3>
                  <p style={{ fontSize: "1rem", color: "#5F8699", lineHeight: 1.7, marginBottom: 24, maxWidth: 420 }}>Select your industry, location, investment size and project stage. The platform identifies all applicable approvals, licences, registrations and NOCs — with no guesswork.</p>
                  <button onClick={onStart} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.875rem", fontWeight: 500, padding: "9px 18px", border: "1.5px solid #C8D9E2", borderRadius: 8, background: "#fff", color: "#2A3D4A", cursor: "pointer", transition: "background 0.15s, border-color 0.15s" }} onMouseEnter={(e) => {
    e.currentTarget.style.background = "#E8F2F6";
    e.currentTarget.style.borderColor = "#5F8699";
  }} onMouseLeave={(e) => {
    e.currentTarget.style.background = "#fff";
    e.currentTarget.style.borderColor = "#C8D9E2";
  }}>
                    Get started <ArrowRight size={14} />
                  </button>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <KnowApprovalsMockup />
                </div>
              </div>
            </RevealSection>
          </div>
        </section>

        {
    /* 02 — Prepare With Confidence — white */
  }
        <section style={{ padding: "72px 24px", background: "#fff", position: "relative", overflow: "hidden" }}>
          <BgDocuments />
          <div style={{ maxWidth: 1160, margin: "0 auto", position: "relative", zIndex: 1 }}>
            <RevealSection>
              <div className="feature-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
                <div style={{ display: "flex", justifyContent: "flex-start" }}>
                  <PrepareDocsMockup />
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#5F8699", letterSpacing: "0.06em", textTransform: "uppercase", display: "block", marginBottom: 14 }}>02 — Prepare With Confidence</span>
                  <h3 style={{ fontSize: "clamp(1.375rem, 2.5vw, 1.875rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#2A3D4A", lineHeight: 1.2, marginBottom: 16 }}>Every document you need, in one checklist.</h3>
                  <p style={{ fontSize: "1rem", color: "#5F8699", lineHeight: 1.7, marginBottom: 24, maxWidth: 420 }}>For each approval, see the exact documents required. Track what you have, what's missing and what to prepare next — before you submit anything.</p>
                  <button onClick={onStart} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.875rem", fontWeight: 500, padding: "9px 18px", border: "1.5px solid #C8D9E2", borderRadius: 8, background: "#fff", color: "#2A3D4A", cursor: "pointer", transition: "background 0.15s, border-color 0.15s" }} onMouseEnter={(e) => {
    e.currentTarget.style.background = "#E8F2F6";
    e.currentTarget.style.borderColor = "#5F8699";
  }} onMouseLeave={(e) => {
    e.currentTarget.style.background = "#fff";
    e.currentTarget.style.borderColor = "#C8D9E2";
  }}>
                    Get started <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </RevealSection>
          </div>
        </section>

        {
    /* 03 — Track Everything — beige */
  }
        <section style={{ padding: "72px 24px", background: "#F6EFE2", position: "relative", overflow: "hidden" }}>
          <BgJourneyLine />
          <div style={{ maxWidth: 1160, margin: "0 auto", position: "relative", zIndex: 1 }}>
            <RevealSection>
              <div className="feature-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#5F8699", letterSpacing: "0.06em", textTransform: "uppercase", display: "block", marginBottom: 14 }}>03 — Track Everything</span>
                  <h3 style={{ fontSize: "clamp(1.375rem, 2.5vw, 1.875rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#2A3D4A", lineHeight: 1.2, marginBottom: 16 }}>A clear roadmap from start to operation.</h3>
                  <p style={{ fontSize: "1rem", color: "#5F8699", lineHeight: 1.7, marginBottom: 24, maxWidth: 420 }}>All your approvals in one visual timeline. See completed, in-progress and upcoming milestones at a glance — and know what to focus on next.</p>
                  <button onClick={onStart} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.875rem", fontWeight: 500, padding: "9px 18px", border: "1.5px solid #C8D9E2", borderRadius: 8, background: "#fff", color: "#2A3D4A", cursor: "pointer", transition: "background 0.15s, border-color 0.15s" }} onMouseEnter={(e) => {
    e.currentTarget.style.background = "#E8F2F6";
    e.currentTarget.style.borderColor = "#5F8699";
  }} onMouseLeave={(e) => {
    e.currentTarget.style.background = "#fff";
    e.currentTarget.style.borderColor = "#C8D9E2";
  }}>
                    Get started <ArrowRight size={14} />
                  </button>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <TrackMockup />
                </div>
              </div>
            </RevealSection>
          </div>
        </section>

        {
    /* 04 — Discover Incentives — white */
  }
        <section id="incentives" style={{ padding: "72px 24px", background: "#fff", position: "relative", overflow: "hidden" }}>
          <BgGrowth />
          <div style={{ maxWidth: 1160, margin: "0 auto", position: "relative", zIndex: 1 }}>
            <RevealSection>
              <div className="feature-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>
                <div style={{ display: "flex", justifyContent: "flex-start" }}>
                  <IncentivesMockup />
                </div>
                <div>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#5F8699", letterSpacing: "0.06em", textTransform: "uppercase", display: "block", marginBottom: 14 }}>04 — Discover Incentives</span>
                  <h3 style={{ fontSize: "clamp(1.375rem, 2.5vw, 1.875rem)", fontWeight: 700, letterSpacing: "-0.02em", color: "#2A3D4A", lineHeight: 1.2, marginBottom: 16 }}>Find schemes and subsidies you qualify for.</h3>
                  <p style={{ fontSize: "1rem", color: "#5F8699", lineHeight: 1.7, marginBottom: 24, maxWidth: 420 }}>Government incentives, capital subsidies and MSME schemes are often missed. The platform surfaces eligible opportunities based on your project profile.</p>
                  <button onClick={onStart} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.875rem", fontWeight: 500, padding: "9px 18px", border: "1.5px solid #C8D9E2", borderRadius: 8, background: "#fff", color: "#2A3D4A", cursor: "pointer", transition: "background 0.15s, border-color 0.15s" }} onMouseEnter={(e) => {
    e.currentTarget.style.background = "#E8F2F6";
    e.currentTarget.style.borderColor = "#5F8699";
  }} onMouseLeave={(e) => {
    e.currentTarget.style.background = "#fff";
    e.currentTarget.style.borderColor = "#C8D9E2";
  }}>
                    Get started <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </RevealSection>
          </div>
        </section>
      </div>

      {
    /* ── HOW IT WORKS ───────────────────────────────────── */
  }
      <section
    id="how-it-works"
    style={{
      padding: "100px 24px",
      background: "#F6EFE2",
      borderTop: "1px solid #D5C9B8",
      borderBottom: "1px solid #D5C9B8"
    }}
  >
        <div style={{ maxWidth: 1160, margin: "0 auto" }}>
          <RevealSection>
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <h2
    style={{
      fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 12
    }}
  >
                How it works
              </h2>
              <p
    style={{
      color: "#5F8699",
      fontSize: "1.0625rem",
      maxWidth: 440,
      margin: "0 auto"
    }}
  >
                Four steps from idea to a clear, actionable approval roadmap.
              </p>
            </div>
          </RevealSection>

          <RevealSection>
            <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 0,
      position: "relative"
    }}
    className="steps-grid"
  >
              <div
    style={{
      position: "absolute",
      top: 28,
      left: "12.5%",
      right: "12.5%",
      height: 1,
      background: "#D5C9B8",
      zIndex: 0
    }}
    className="steps-line"
  />
              {[
    {
      n: "01",
      label: "Tell us about your project",
      body: "Describe your industrial activity, location and scale."
    },
    {
      n: "02",
      label: "Get your personalised roadmap",
      body: "We identify every applicable approval and requirement."
    },
    {
      n: "03",
      label: "Prepare and apply",
      body: "Follow document checklists and process guidance."
    },
    {
      n: "04",
      label: "Track your progress",
      body: "Monitor every approval from pending to complete."
    }
  ].map((step) => <div
    key={step.n}
    style={{
      textAlign: "center",
      padding: "0 24px",
      position: "relative",
      zIndex: 1
    }}
  >
                  <div
    style={{
      width: 56,
      height: 56,
      borderRadius: "50%",
      background: "#fff",
      border: "1.5px solid #BDD2DB",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      margin: "0 auto 20px",
      boxShadow: "0 2px 8px rgba(42,61,74,0.08)"
    }}
  >
                    <span
    style={{
      fontSize: "1.125rem",
      fontWeight: 800,
      color: "#5F8699",
      letterSpacing: "-0.02em"
    }}
  >
                      {step.n}
                    </span>
                  </div>
                  <h3
    style={{
      fontWeight: 700,
      fontSize: "0.9375rem",
      color: "#2A3D4A",
      marginBottom: 8,
      lineHeight: 1.3
    }}
  >
                    {step.label}
                  </h3>
                  <p
    style={{
      fontSize: "0.875rem",
      color: "#5F8699",
      lineHeight: 1.6,
      margin: 0
    }}
  >
                    {step.body}
                  </p>
                </div>)}
            </div>
          </RevealSection>

          <RevealSection style={{ textAlign: "center", marginTop: 52 }}>
            <button
    style={tealBtn}
    onClick={onStart}
    className="hero-cta-primary"
  >
              Get My Approval Roadmap
              <ArrowRight size={16} />
            </button>
          </RevealSection>
        </div>
      </section>

      {
    /* ── AI + HUMAN SUPPORT ─────────────────────────────── */
  }
      <section style={{ padding: "100px 24px", background: "#fff" }}>
        <div style={{ maxWidth: 820, margin: "0 auto", textAlign: "center" }}>
          <RevealSection>
            <h2
    style={{
      fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 12
    }}
  >
              Get help when you need it.
            </h2>
            <p
    style={{
      fontSize: "1.0625rem",
      color: "#5F8699",
      lineHeight: 1.7,
      marginBottom: 48
    }}
  >
              Unsure about a requirement? Get guided assistance throughout your
              approval journey.
            </p>

            <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 20,
      textAlign: "left",
      marginBottom: 36
    }}
    className="support-grid"
  >
              {[
    {
      icon: <Sparkles size={20} color="#5F8699" />,
      bg: "#E8F1F4",
      label: "AI Guidance",
      body: "Understand requirements, documents and next steps through intelligent, context-aware guidance."
    },
    {
      icon: <Users size={20} color="#3D8A6A" />,
      bg: "#E4F5EE",
      border: "#B0D9C8",
      label: "Human Support",
      body: "Connect with a support representative when you need personalised help with your approval journey."
    }
  ].map((card) => <div
    key={card.label}
    style={{
      padding: 28,
      background: "#fff",
      border: "1.5px solid #C8D9E2",
      borderRadius: 12,
      transition: "box-shadow 0.2s, transform 0.2s",
      cursor: "default"
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.boxShadow = "0 4px 16px rgba(42,61,74,0.09)";
      e.currentTarget.style.transform = "translateY(-2px)";
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.boxShadow = "none";
      e.currentTarget.style.transform = "translateY(0)";
    }}
  >
                  <div
    style={{
      width: 44,
      height: 44,
      background: card.bg,
      border: `1px solid ${card.border}`,
      borderRadius: 12,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 16
    }}
  >
                    {card.icon}
                  </div>
                  <h3
    style={{
      fontWeight: 700,
      fontSize: "1rem",
      color: "#2A3D4A",
      marginBottom: 8
    }}
  >
                    {card.label}
                  </h3>
                  <p
    style={{
      fontSize: "0.9rem",
      color: "#5F8699",
      lineHeight: 1.65,
      margin: 0
    }}
  >
                    {card.body}
                  </p>
                </div>)}
            </div>

            <button
    style={tealBtn}
    onClick={onStart}
    className="hero-cta-primary"
  >
              Get Assistance
              <ArrowRight size={16} />
            </button>
          </RevealSection>
        </div>
      </section>

      {
    /* ── RESOURCES ─────────────────────────────────────────── */
  }
      <section
    id="resources"
    style={{
      padding: "100px 24px",
      background: "#F6EFE2",
      borderTop: "1px solid #D5C9B8",
      borderBottom: "1px solid #D5C9B8"
    }}
  >
        <div style={{ maxWidth: 1160, margin: "0 auto" }}>
          <RevealSection>
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <h2
    style={{
      fontSize: "clamp(1.75rem, 3vw, 2.25rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 12
    }}
  >
                Everything connected in one place.
              </h2>
              <p
    style={{
      color: "#5F8699",
      fontSize: "1rem",
      maxWidth: 440,
      margin: "0 auto"
    }}
  >
                Official resources, forms and application links — accessible
                from your dashboard.
              </p>
            </div>
          </RevealSection>
          <RevealSection>
            <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
      gap: 14
    }}
  >
              {[
    {
      icon: <Building2 size={20} />,
      label: "Government Portals",
      body: "Direct links to official ministry and department portals."
    },
    {
      icon: <FileText size={20} />,
      label: "Official Forms",
      body: "Download application forms for each approval category."
    },
    {
      icon: <Shield size={20} />,
      label: "Guidelines",
      body: "Plain-language summaries of regulatory requirements."
    },
    {
      icon: <LayoutDashboard size={20} />,
      label: "Notifications",
      body: "Policy updates, fee changes and deadline alerts."
    },
    {
      icon: <ExternalLink size={20} />,
      label: "Application Links",
      body: "Direct links to apply online where portals support it."
    }
  ].map((card) => <div
    key={card.label}
    className="card card-hover"
    style={{
      padding: 22,
      display: "flex",
      flexDirection: "column",
      gap: 12,
      background: "#fff"
    }}
  >
                  <div
    style={{
      width: 40,
      height: 40,
      background: "#E8F1F4",
      borderRadius: 10,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#5F8699"
    }}
  >
                    {card.icon}
                  </div>
                  <div>
                    <div
    style={{
      fontWeight: 600,
      fontSize: "0.9rem",
      color: "#2A3D4A",
      marginBottom: 4
    }}
  >
                      {card.label}
                    </div>
                    <p
    style={{
      fontSize: "0.8125rem",
      color: "#5F8699",
      margin: 0,
      lineHeight: 1.55
    }}
  >
                      {card.body}
                    </p>
                  </div>
                </div>)}
            </div>
          </RevealSection>
        </div>
      </section>

      {
    /* ── TESTIMONIALS + STATS ───────────────────────────── */
  }
      <section style={{ padding: "100px 24px", background: "#fff" }}>
        <div style={{ maxWidth: 1160, margin: "0 auto" }}>
          <RevealSection>
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <h2
    style={{
      fontSize: "clamp(1.75rem, 3vw, 2.25rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 12
    }}
  >
                Designed to make complex processes feel simple.
              </h2>
            </div>
          </RevealSection>

          <RevealSection>
            <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 1,
      background: "#D5C9B8",
      border: "1px solid #D5C9B8",
      borderRadius: 16,
      overflow: "hidden",
      marginBottom: 56
    }}
    className="stats-grid"
  >
              {[
    { value: "18+", label: "Approval Categories" },
    { value: "Multiple", label: "Government Departments" },
    { value: "One", label: "Personalised Roadmap" }
  ].map((stat) => <div key={stat.label} style={{ background: "#fff", padding: "36px 24px", textAlign: "center" }}>
                  <div
    style={{
      fontSize: "2.25rem",
      fontWeight: 800,
      color: "#5F8699",
      letterSpacing: "-0.03em",
      lineHeight: 1,
      marginBottom: 8
    }}
  >
                    {stat.value}
                  </div>
                  <div
    style={{
      fontSize: "0.9rem",
      color: "#8BA3AE",
      fontWeight: 500
    }}
  >
                    {stat.label}
                  </div>
                </div>)}
            </div>
          </RevealSection>

          <RevealSection>
            <div
    style={{
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20
    }}
    className="testimonial-grid"
  >
              {[
    {
      quote: "I had no idea where to start with government approvals. This platform gave me a clear list and showed me exactly what to prepare.",
      name: "Rohit M.",
      role: "MSME Founder, Pune"
    },
    {
      quote: "The document checklist saved me weeks of back-and-forth. Everything I needed was laid out step by step.",
      name: "Priya K.",
      role: "Industrial Entrepreneur, Hyderabad"
    },
    {
      quote: "Finally a platform that explains government processes in plain language. The roadmap view made everything feel manageable.",
      name: "Vikram S.",
      role: "Manufacturing Unit Owner, Rajkot"
    }
  ].map((t) => <div
    key={t.name}
    style={{
      padding: 28,
      background: "#fff",
      border: "1.5px solid #C8D9E2",
      borderRadius: 12
    }}
  >
                  <p
    style={{
      fontSize: "0.9375rem",
      color: "#2A3D4A",
      lineHeight: 1.7,
      fontStyle: "italic",
      marginBottom: 20
    }}
  >
                    "{t.quote}"
                  </p>
                  <div>
                    <div
    style={{
      fontWeight: 600,
      fontSize: "0.875rem",
      color: "#2A3D4A"
    }}
  >
                      {t.name}
                    </div>
                    <div style={{ fontSize: "0.8125rem", color: "#8BA3AE" }}>
                      {t.role}
                    </div>
                  </div>
                </div>)}
            </div>
          </RevealSection>
        </div>
      </section>

      {
    /* ── FINAL CTA ──────────────────────────────────────── */
  }
      <section
    style={{
      padding: "80px 24px",
      background: "#F6EFE2",
      borderTop: "1px solid #D5C9B8"
    }}
  >
        <RevealSection>
          <div style={{ maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
            <h2
    style={{
      fontSize: "clamp(1.75rem, 3vw, 2.25rem)",
      fontWeight: 800,
      letterSpacing: "-0.02em",
      color: "#2A3D4A",
      marginBottom: 14
    }}
  >
              Ready to simplify your industrial journey?
            </h2>
            <p
    style={{
      fontSize: "1rem",
      color: "#5F8699",
      lineHeight: 1.7,
      marginBottom: 36
    }}
  >
              Find the approvals, requirements and opportunities relevant to your
              project.
            </p>
            <div
    style={{
      display: "flex",
      justifyContent: "center",
      gap: 12,
      flexWrap: "wrap"
    }}
  >
              <button
    style={tealBtn}
    onClick={onStart}
    className="hero-cta-primary"
  >
                Get Started
                <ArrowRight size={16} />
              </button>
              <button
    style={outlineBtn}
    onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}
    className="hero-cta-secondary"
  >
                Explore Approvals
              </button>
            </div>
          </div>
        </RevealSection>
      </section>

      <style>{`
        @media (max-width: 900px) {
          .hero-grid { grid-template-columns: 1fr !important; gap: 40px !important; padding: 48px 32px !important; }
          .hero-mockup { display: none; }
          .feature-row { grid-template-columns: 1fr !important; direction: ltr !important; gap: 32px !important; margin-bottom: 60px !important; }
          .steps-grid { grid-template-columns: 1fr 1fr !important; gap: 32px !important; }
          .steps-line { display: none !important; }
          .support-grid { grid-template-columns: 1fr !important; }
          .stats-grid { grid-template-columns: 1fr !important; }
          .testimonial-grid { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 600px) {
          .steps-grid { grid-template-columns: 1fr !important; }
        }

        /* Teal CTA hover states */
        .hero-cta-primary:hover {
          background: #4d6f82 !important;
          border-color: #4d6f82 !important;
          box-shadow: 0 4px 18px rgba(95,134,153,0.38) !important;
          transform: translateY(-1px);
        }
        .hero-cta-primary:active { transform: translateY(1px) !important; }
        .hero-cta-secondary:hover {
          background: #E8F1F4 !important;
          border-color: #5F8699 !important;
          transform: translateY(-1px);
        }
        .hero-cta-secondary:active { transform: translateY(1px) !important; }


        /* Carousel */
        .carousel-track {
          scrollbar-width: none;
          -ms-overflow-style: none;
        }
        .carousel-track::-webkit-scrollbar { display: none; }
        .carousel-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 28px rgba(42,61,74,0.13) !important;
        }
        .carousel-card:hover img { transform: scale(1.04); }
        @media (max-width: 640px) {
          .carousel-card { width: calc(100vw - 64px) !important; }
        }

        /* Hero background node animations */
        .hero-nodes circle:nth-child(1) { animation: heroNodeFloat 4.2s ease-in-out infinite; }
        .hero-nodes circle:nth-child(2) { animation: heroNodeFloat 4.8s ease-in-out 0.6s infinite; }
        .hero-nodes circle:nth-child(3) { animation: heroNodeFloat 3.9s ease-in-out 1.2s infinite; }
        .hero-nodes circle:nth-child(4) { animation: heroNodeFloat 5.1s ease-in-out 1.8s infinite; }
        .hero-nodes circle:nth-child(5) { animation: heroNodeFloat 4.5s ease-in-out 2.4s infinite; }

        .hero-graph circle:nth-child(odd)  { animation: heroGraphPulse 6.5s ease-in-out infinite; }
        .hero-graph circle:nth-child(even) { animation: heroGraphPulse 6.5s ease-in-out 1.5s infinite; }

        @keyframes heroNodeFloat {
          0%, 100% { transform: translateY(0px); opacity: 0.32; }
          50%       { transform: translateY(-4px); opacity: 0.56; }
        }
        @keyframes heroGraphPulse {
          0%, 100% { opacity: 0.088; }
          50%       { opacity: 0.16; }
        }
      `}</style>
    </div>;
}
export {
  Home as default
};
