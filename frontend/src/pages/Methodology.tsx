import { PageTitle } from "../components/shared";
export default function Methodology() {
  return (
    <>
      <PageTitle
        eyebrow="HOW THREATGRAPH REASONS"
        title="Evidence first. Certainty earned."
        text="An uncertainty-aware approach to multimodal digital investigation."
      />
      <div className="methodology card">
        <h2>Follow the content</h2>
        <p>
          A bounded investigation discovers redirects, embedded media, and QR
          destinations. Each finding retains its source, asset, confidence, and
          detector version. Untrusted page scripts and downloaded programs are
          never executed.
        </p>
        <h2>Keep risk and confidence separate</h2>
        <p>
          Risk describes observed indicators. Confidence describes the strength
          of available evidence. Missing models and incomplete analysis increase
          uncertainty and can produce an INCONCLUSIVE verdict. Synthetic content
          does not, by itself, establish fraud.
        </p>
        <h2>Expose disagreement</h2>
        <p>
          Strongly opposing predictions about the same asset and hypothesis
          create explicit conflicts. Audio and visual predictions may indicate
          dubbing or voice manipulation. Missing EXIF or Content Credentials is
          neutral and is not a conflict.
        </p>
        <h2>Be clear about the baseline</h2>
        <p>
          The default fusion is a transparent, uncalibrated conservative rule:
          take the strongest confidence-weighted category contribution. It does
          not claim research superiority. Learned fusion and ablations must be
          trained and evaluated on independently labeled investigations before
          deployment.
        </p>
        <h2>Respect scope and privacy</h2>
        <p>
          This is a local, single-user research workspace. There is no public
          multi-tenant authentication layer. Do not expose it publicly without
          an authenticated gateway. Uploaded content stays local; URL analysis
          necessarily contacts the submitted public host. Original uploads
          expire under the configured retention policy.
        </p>
        <h2>Know what remains unknown</h2>
        <p>
          Models may fail on new generators, codecs, languages, or compression.
          Scores are not forensic proof. The registry reports actual installed
          model coverage, and unavailable integrations remain visible in the
          report.
        </p>
      </div>
    </>
  );
}
