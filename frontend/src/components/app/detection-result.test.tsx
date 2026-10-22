import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DetectionResult } from "./detection-result";
import type { VideoDetectionDto } from "@/lib/api";

const detection: VideoDetectionDto = {
  id: "one",
  class_id: 1,
  class_name: "YOLO label",
  confidence: 0.9,
  track_id: null,
  product_id: "product-one",
  identity_status: "identified",
  identity_confidence: 0.85,
  category: "Shampoo",
  brand: "Sunsilk",
  variant: null,
  package_size: "160ml",
  barcode: null,
  bbox: { x1: 0, y1: 0, x2: 1, y2: 1 },
  normalized_bbox: { x1: 0, y1: 0, x2: 1, y2: 1 },
  identity_evidence: {
    catalog_name: "Sunsilk Shampoo 160ml",
    ocr_tokens: ["SUNSILK"],
    florence_description: "A shampoo bottle",
    method: "multimodal_consensus",
  },
};
describe("product result evidence", () => {
  it("shows the catalog identity and both independent evidence outputs", () => {
    const html = renderToStaticMarkup(<DetectionResult detection={detection} />);
    expect(html).toContain("Sunsilk Shampoo 160ml");
    expect(html).toContain("SUNSILK");
    expect(html).toContain("A shampoo bottle");
    expect(html).toContain("not a probability");
  });
  it("does not present an ambiguous detector label as confirmed", () => {
    const html = renderToStaticMarkup(
      <DetectionResult
        detection={{ ...detection, product_id: null, identity_status: "ambiguous" }}
      />,
    );
    expect(html).toContain("Product needs review");
    expect(html).not.toContain("Sunsilk Shampoo 160ml");
  });
  it("distinguishes unavailable providers from recorded evidence", () => {
    const html = renderToStaticMarkup(
      <DetectionResult
        detection={{
          ...detection,
          identity_evidence: { provider_errors: ["ocr_unavailable", "florence_unavailable"] },
        }}
      />,
    );
    expect(html).toContain("OCR was unavailable");
    expect(html).toContain("Florence was unavailable");
  });
});
