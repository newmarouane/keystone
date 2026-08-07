import express from "express";
import { chromium } from "playwright";

const app = express();

let browser;

async function getBrowser() {
  if (!browser) {
    browser = await chromium.launch({
      headless: true
    });
  }

  return browser;
}

app.get("/", async (req, res) => {
  const target = req.query.url;

  if (!target) {
    return res.status(400).json({
      error: "Missing url"
    });
  }

  let page;

  try {
    const browser = await getBrowser();

    let page = await browser.newPage();

await page.goto("https://medias24.com/", {
  waitUntil: "domcontentloaded",
  timeout: 30000
});

console.log("Homepage:", await page.title());
console.log("URL:", page.url());

await page.waitForTimeout(10000);

console.log(
  "Cookies:",
  await page.context().cookies()
);
    
    page = await browser.newPage({
      userAgent:
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
        "AppleWebKit/537.36 (KHTML, like Gecko) " +
        "Chrome/150.0.0.0 Safari/537.36",
      viewport: {
        width: 1366,
        height: 768
      }
    });

    console.log("Opening:", target);

    const response = await page.goto(target, {
      waitUntil: "domcontentloaded",
      timeout: 30000
    });

    console.log("HTTP status:", response?.status());
    console.log("Final URL:", page.url());
    console.log("Title:", await page.title());

    await page.waitForTimeout(10000);

    const title = await page.title();
    const html = await page.content();

    console.log("After wait:");
    console.log("URL:", page.url());
    console.log("Title:", title);
    console.log("HTML length:", html.length);

    res.json({
      status: response?.status(),
      url: page.url(),
      title,
      content: await page.locator("body").innerText()
    });

  } catch (error) {
    console.error(error);

    res.status(500).json({
      error: error.message
    });

  } finally {
    if (page) {
      await page.close();
    }
  }
});

app.listen(process.env.PORT || 3000, "0.0.0.0", () => {
  console.log("Server started");
});
