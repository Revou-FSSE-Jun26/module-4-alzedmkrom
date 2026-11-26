import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";

function Host({ onClose }: { onClose: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <BaseButton onClick={() => setOpen(true)}>Open</BaseButton>
      <BaseModal
        open={open}
        title="Edit"
        onClose={() => {
          onClose();
          setOpen(false);
        }}
      >
        <BaseButton>Inside</BaseButton>
      </BaseModal>
    </>
  );
}

describe("BaseModal (FE-UI-03)", () => {
  it("ignores Escape and backdrop click while dismissDisabled (a submit is pending)", () => {
    const onClose = vi.fn();
    const { container } = render(
      <BaseModal open title="Saving" onClose={onClose} dismissDisabled>
        <BaseButton>Inside</BaseButton>
      </BaseModal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    const backdrop = container.ownerDocument.querySelector('[aria-hidden="true"].absolute');
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop as Element);
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog", { name: "Saving" })).toBeInTheDocument();
  });

  it("closes on Escape again once dismissDisabled is cleared", () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <BaseModal open title="Saving" onClose={onClose} dismissDisabled>
        <BaseButton>Inside</BaseButton>
      </BaseModal>,
    );
    rerender(
      <BaseModal open title="Saving" onClose={onClose} dismissDisabled={false}>
        <BaseButton>Inside</BaseButton>
      </BaseModal>,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders as a labelled dialog", () => {
    render(<Host onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    const dialog = screen.getByRole("dialog", { name: "Edit" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(<Host onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("returns focus to the trigger when it closes", () => {
    render(<Host onClose={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Open" });
    trigger.focus();
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(document.activeElement).toBe(trigger);
  });
});
