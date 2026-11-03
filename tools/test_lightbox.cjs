"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createViewer } = require("../docs/assets/javascripts/lightbox.js");

function fixture() {
  let doc;
  class Element {
    constructor(tag) { this.tagName = tag.toUpperCase(); this.attrs = {}; this.style = {}; this.events = {}; this.isConnected = true; this.children = []; this.open = false; }
    setAttribute(key, value) { this.attrs[key] = value; }
    getAttribute(key) { return this.attrs[key] ?? null; }
    removeAttribute(key) { delete this.attrs[key]; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, fn) { (this.events[name] ??= []).push(fn); }
    emit(name, event = {}) { for (const fn of this.events[name] ?? []) fn({ type: name, target: this, preventDefault() { this.prevented = true; }, ...event }); }
    focus() { doc.activeElement = this; }
    showModal() { this.open = true; }
    close() { this.open = false; this.emit("close"); }
    closest(selector) {
      if (selector === "figure") return this.figure ?? null;
      if (selector === "a") return this.anchor ?? null;
      if (selector.includes('aria-haspopup="dialog"')) return this.attrs["aria-haspopup"] === "dialog" ? this : this.anchor ?? null;
      return null;
    }
    querySelector(selector) { if (selector === "figcaption") return this.caption; if (selector === "img") return this.source; return null; }
  }
  doc = new Element("document");
  doc.body = new Element("body");
  doc.documentElement = new Element("html");
  doc.documentElement.clientWidth = 1265;
  doc.createElement = (tag) => new Element(tag);
  const source = new Element("img");
  source.src = "http://localhost/figure-001.png";
  source.alt = "Рисунок 1 — Вход в систему.";
  source.figure = new Element("figure");
  source.figure.caption = { textContent: source.alt };
  doc.querySelectorAll = () => [source];
  const win = new Element("window");
  Object.assign(win, { scrollX: 0, scrollY: 812, innerWidth: 1280, getComputedStyle: () => ({ paddingRight: "0px" }), scrollCalls: [] });
  win.scrollTo = (value) => win.scrollCalls.push(value);
  const viewer = createViewer(doc, win);
  viewer.prepare();
  return { doc, win, viewer, source, Element };
}

test("figures have keyboard activation and dialog semantics", () => {
  const { source, viewer } = fixture();
  assert.equal(source.attrs.role, "button");
  assert.equal(source.attrs.tabindex, "0");
  assert.equal(source.attrs["aria-haspopup"], "dialog");
  assert.equal(viewer.dialog.attrs["aria-label"], "Просмотр рисунка");
});

test("opening locks scroll, focuses close button and retains image caption", () => {
  const { doc, viewer, source } = fixture();
  doc.emit("click", { target: source, button: 0 });
  assert.equal(viewer.dialog.open, true);
  assert.equal(doc.activeElement, viewer.closeButton);
  assert.equal(doc.body.style.top, "-812px");
  assert.equal(viewer.image.src, source.src);
  assert.equal(viewer.image.alt, source.alt);
});

for (const mode of ["button", "backdrop", "image", "escape"]) {
  test(`closing by ${mode} restores styles, reading position and trigger focus`, () => {
    const { doc, win, viewer, source } = fixture();
    doc.body.setAttribute("style", "color: red");
    viewer.open(source, source);
    if (mode === "button") viewer.closeButton.emit("click");
    if (mode === "backdrop") viewer.dialog.emit("click");
    if (mode === "image") viewer.dialog.emit("click", { target: viewer.image });
    if (mode === "escape") viewer.dialog.emit("cancel");
    assert.equal(viewer.dialog.open, false);
    assert.equal(doc.body.getAttribute("style"), "color: red");
    assert.equal(doc.documentElement.getAttribute("style"), null);
    assert.equal(doc.activeElement, source);
    assert.deepEqual(win.scrollCalls, [{ left: 0, top: 812, behavior: "instant" }]);
  });
}

test("instant navigation closes without restoring old route position", () => {
  const { doc, win, viewer, source } = fixture();
  viewer.open(source, source);
  viewer.prepare();
  assert.equal(viewer.dialog.open, false);
  assert.equal(win.scrollCalls.length, 0);
  assert.equal(doc.body.getAttribute("style"), null);
});

for (const key of ["Enter", " "]) {
  test(`keyboard ${JSON.stringify(key)} opens a figure`, () => {
    const { doc, source, viewer } = fixture();
    doc.emit("keydown", { target: source, key });
    assert.equal(viewer.dialog.open, true);
  });
}

test("Tab and Shift+Tab remain inside the dialog", () => {
  const { doc, source, viewer } = fixture();
  viewer.open(source, source);
  for (const shiftKey of [false, true]) {
    viewer.dialog.emit("keydown", { key: "Tab", shiftKey });
    assert.equal(doc.activeElement, viewer.closeButton);
  }
});

test("decorative images and modified clicks are not intercepted", () => {
  const { doc, source, viewer, Element } = fixture();
  doc.emit("click", { target: new Element("img"), button: 0 });
  doc.emit("click", { target: source, button: 0, ctrlKey: true });
  assert.equal(viewer.dialog.open, false);
});

test("linked images also open from keyboard on the link", () => {
  const { doc, source, viewer, Element } = fixture();
  const anchor = new Element("a");
  anchor.source = source;
  source.anchor = anchor;
  viewer.prepare();
  doc.emit("keydown", { target: anchor, key: "Enter" });
  assert.equal(viewer.dialog.open, true);
});
