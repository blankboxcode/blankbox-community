/* eslint-disable @next/next/no-img-element -- Brand assets are shared with the local Vite build. */

type Props = {
  responsive?: boolean;
  className?: string;
};

export function BrandLogo({ responsive = false, className = "" }: Props) {
  return (
    <span className={`brand-logo ${responsive ? "brand-logo-responsive" : ""} ${className}`.trim()}>
      <img
        className="brand-logo-wordmark"
        src="/brand/blankbox-logo-light.png"
        alt="Blank Box"
        width="550"
        height="240"
      />
      {responsive ? (
        <img
          className="brand-logo-profile"
          src="/brand/blankbox-profile-192.png"
          alt=""
          width="192"
          height="192"
          aria-hidden="true"
        />
      ) : null}
    </span>
  );
}
