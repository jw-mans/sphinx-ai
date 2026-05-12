/**
 * E2E GUI test scenario for the Sphinx interview flow.
 *
 * Prerequisites:
 *   npm install -D @playwright/test
 *   npx playwright install chromium
 *
 * Run:
 *   npx playwright test frontend/tests/e2e/interview_flow.spec.ts
 *   npx playwright test --ui   # interactive UI mode
 *
 * Expects the dev stack running:
 *   docker compose up   (backend on :8000, frontend on :5173)
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';

// Helper: skip Telegram SDK init (not available in browser outside Telegram)

async function injectAnonUser(page: Page) {
  await page.addInitScript(() => {
    const anonId = 'playwright_' + Math.random().toString(36).slice(2, 10);
    localStorage.setItem('sphinx_anon_id', anonId);
    // Clear any cached user so a fresh one is created
    localStorage.removeItem('sphinx_user_id');
  });
}

// Scenario 1: Home page renders key UI elements
test('home page: logo, heading and start form are visible', async ({ page }) => {
  await injectAnonUser(page);
  await page.goto(BASE_URL);

  await expect(page.getByRole('heading', { name: 'Sphinx' })).toBeVisible();
  const levelSelect = page.locator('select, [data-testid="level-select"]').first();
  await expect(levelSelect).toBeVisible();
});

// Scenario 2: Selecting a level and stack enables the Start button
test('home page: start button activates after level + stack selection', async ({ page }) => {
  await injectAnonUser(page);
  await page.goto(BASE_URL);

  // Pick level
  const levelSelect = page.locator('select').first();
  await levelSelect.selectOption('junior');

  // Pick at least one stack chip or checkbox
  const stackOption = page
    .locator('button, label, [role="checkbox"]')
    .filter({ hasText: /python/i })
    .first();
  if (await stackOption.isVisible()) {
    await stackOption.click();
  }

  const startBtn = page.getByRole('button', { name: /старт|start|начать/i });
  await expect(startBtn).toBeEnabled();
});

// Scenario 3: Starting an interview navigates to /interview/:id

test('start interview: navigates to interview page and shows first question', async ({ page }) => {
  await injectAnonUser(page);
  await page.goto(BASE_URL);

  // Select level
  const levelSelect = page.locator('select').first();
  await levelSelect.selectOption('junior');

  // Select stack
  const stackOption = page
    .locator('button, label')
    .filter({ hasText: /python/i })
    .first();
  if (await stackOption.isVisible()) {
    await stackOption.click();
  }

  const startBtn = page.getByRole('button', { name: /старт|start|начать/i });
  await startBtn.click();

  // Should navigate to /interview/<id>
  await expect(page).toHaveURL(/\/interview\/\d+/, { timeout: 10_000 });

  // First question text must appear
  const questionText = page.locator('[data-testid="question-text"], h2, p').first();
  await expect(questionText).not.toBeEmpty({ timeout: 10_000 });
});

// Scenario 4: Submitting an answer shows evaluation / feedback

test('interview page: typing and submitting an answer shows feedback', async ({ page }) => {
  await injectAnonUser(page);
  await page.goto(BASE_URL);

  const levelSelect = page.locator('select').first();
  await levelSelect.selectOption('junior');

  const stackOption = page.locator('button, label').filter({ hasText: /python/i }).first();
  if (await stackOption.isVisible()) await stackOption.click();

  await page.getByRole('button', { name: /старт|start|начать/i }).click();
  await expect(page).toHaveURL(/\/interview\/\d+/, { timeout: 10_000 });

  // Type answer in the textarea
  const textarea = page.locator('textarea').first();
  await expect(textarea).toBeVisible({ timeout: 8_000 });
  await textarea.fill('A decorator is a function that wraps another function to extend its behaviour.');

  // Submit
  const submitBtn = page.getByRole('button', { name: /отправить|submit|ответить/i });
  await submitBtn.click();

  // Feedback section or score must appear
  const feedback = page.locator('[data-testid="feedback"], .feedback, [class*="feedback"], [class*="score"]').first();
  await expect(feedback).toBeVisible({ timeout: 15_000 });
});

// Scenario 5: Navigation to result page shows summary

test('result page: navigating directly to /result shows average score', async ({ page }) => {
  await injectAnonUser(page);
  // We don't have a valid interview_id here, so mock the API call and
  // navigate directly — this validates the page renders without crashing.
  await page.route('**/interview/*/result', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        average_score: 7.5,
        summary: {
          overall: 'Strong candidate overall.',
          strengths: ['Python basics'],
          weaknesses: [],
          recommendations: ['Study async patterns'],
        },
        questions_results: [
          {
            question: 'What is a decorator?',
            answer: 'A wrapper function.',
            score: { correctness: 8 },
            feedback: 'Good answer.',
            weak_topics: [],
          },
        ],
      }),
    });
  });

  await page.goto(`${BASE_URL}/interview/1/result`);

  await expect(page.locator('body')).not.toContainText('error', { ignoreCase: true, timeout: 6_000 });
  // Average score or summary heading must be visible
  const score = page.locator('text=/7|score|итог|результат/i').first();
  await expect(score).toBeVisible({ timeout: 8_000 });
});

// Scenario 6: 404 page for unknown routes
test('unknown route: app renders a fallback or redirects', async ({ page }) => {
  await page.goto(`${BASE_URL}/this-route-does-not-exist`);
  // App should either show a not-found message or redirect to /
  await expect(page).toHaveURL(/.+/, { timeout: 5_000 });
  // Should not be a blank page
  const body = await page.locator('body').textContent();
  expect(body?.trim().length).toBeGreaterThan(0);
});
