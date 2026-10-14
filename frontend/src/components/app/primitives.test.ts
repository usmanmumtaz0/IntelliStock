import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Panel, PageHeader, CountDisplay } from "./primitives";
import { ActionButton, Field } from "./operation-fields";

describe("shared console presentation", () => {
  it("preserves explicit panel padding for edge-to-edge tables", () => {
    const html = renderToStaticMarkup(
      createElement(Panel, { title: "Inventory", bodyClassName: "p-0", children: "Rows" }),
    );
    expect(html).toContain('<div class="p-0">Rows</div>');
    expect(html).toContain("<h2");
  });
  it("renders one clear page heading and supporting description", () => {
    const html = renderToStaticMarkup(
      createElement(PageHeader, { title: "Reports", description: "Review recorded inventory" }),
    );
    expect(html).toContain("<h1");
    expect(html).toContain("Review recorded inventory");
  });
  it("keeps form semantics and disabled controls", () => {
    const html = renderToStaticMarkup(
      createElement(Field, { label: "Quantity", name: "quantity", type: "number", required: true }),
    );
    expect(html).toContain("<label");
    expect(html).toContain('name="quantity"');
    expect(html).toContain('required=""');
    const button = renderToStaticMarkup(
      createElement(ActionButton, { disabled: true, children: "Save" }),
    );
    expect(button).toContain('type="button"');
    expect(button).toContain('disabled=""');
  });
  it("does not describe manual committed counts as camera verified", () => {
    const html = renderToStaticMarkup(createElement(CountDisplay, { count: 12 }));
    expect(html).toContain("may include manual corrections");
    expect(html).not.toContain("Verified count");
  });
});
