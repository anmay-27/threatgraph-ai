export default function SignalOrb() {
  return <div className="signal-orb" aria-hidden="true">
    <svg viewBox="0 0 200 200" fill="none">
      <defs><linearGradient id="signal-gradient" x1="20" y1="20" x2="180" y2="180" gradientUnits="userSpaceOnUse"><stop stopColor="#60d5dd"/><stop offset=".5" stopColor="#7871f5"/><stop offset="1" stopColor="#d08fec"/></linearGradient></defs>
      <g className="orb-rings" stroke="url(#signal-gradient)"><ellipse cx="100" cy="100" rx="74" ry="27" transform="rotate(35 100 100)"/><ellipse cx="100" cy="100" rx="74" ry="27" transform="rotate(95 100 100)"/><ellipse cx="100" cy="100" rx="74" ry="27" transform="rotate(155 100 100)"/><circle cx="100" cy="100" r="57" strokeDasharray="2 9"/></g>
      <path d="M100 68C103 90 110 97 132 100C110 103 103 110 100 132C97 110 90 103 68 100C90 97 97 90 100 68Z" fill="url(#signal-gradient)"/>
      <circle cx="40" cy="57" r="4" fill="#7770df"/><circle cx="161" cy="139" r="4" fill="#359897"/>
    </svg>
  </div>;
}
