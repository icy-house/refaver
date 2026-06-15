# Homebrew formula for the refaver CLI (Phase 1).
#
# Lives in a tap repo (e.g. github.com/icy-house/homebrew-tap) as Formula/refaver.rb.
# Install:  brew install icy-house/tap/refaver
#
# The release workflow updates `url` and `sha256` on each tagged release.
class Refaver < Formula
  include Language::Python::Virtualenv

  desc "Reset Safari's cached favicons for a site — no Terminal gymnastics"
  homepage "https://github.com/icy-house/refaver"
  url "https://github.com/icy-house/refaver/releases/download/v0.1.0/refaver-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_SHA256_FROM_RELEASE"
  license "MIT"

  depends_on "python@3.12"
  depends_on :macos

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "refaver", shell_output("#{bin}/refaver --version")
  end
end
