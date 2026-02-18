# Homepage & FAQ Implementation Plan (Mobile-first)

## ✅ Phase 1 (Completed)
1. Added a dedicated FAQ page in React at `/faqs`.
2. Connected FAQ navigation links in both Navbar and Footer.
3. Used existing backend FAQ data from `server/assistant/data/updated_faq.json` only (no new FAQ content added).
4. Split FAQ content into readable front-end sections and rendered mobile-friendly accordion cards.
5. Added FAQ search by question/answer text for quicker mobile use.

## ✅ Phase 2 (Completed)
1. Homepage empty states for low/no product data:
   - Added fallback category cards and featured collection cards.
   - Added clear copy + CTA so sections never look broken.
2. Improved hero for test/low-data phase:
   - Added trust badges and quick credibility stats.
   - Added campaign-style fallback hero visual when product image is not available.
   - Reduced top/hero spacing for better mobile first impression.

## ✅ Phase 3 (Completed)
1. Added modern merchandising blocks:
   - Trending products shelf.
   - New arrivals shelf.
   - Best value picks.
2. Added Giggy AI (G-I-G-I) differentiator section as a core marketplace value proposition.
3. Added responsive behavior for mobile and laptop viewport adaptation using viewport detection.

## ✅ Phase 4 (Completed)
1. Added swipe-friendly product rails for mobile merchandising cards (horizontal scroll + snap).
2. Added sticky bottom mobile shortcuts (Shop, FAQs, GIGI AI) for one-hand navigation.
3. Reduced mobile visual weight (smaller headings/buttons/cards) so pages look less zoomed while desktop remains richer.

## ✅ Phase 5 (Completed)
1. Added Recently Viewed products section on homepage using local browser history storage.
2. Added “For You” personalized picks shelf powered by available inventory/category heuristics.
3. Added dynamic activity banner that adapts messaging by user role and engagement state.

## ✅ Phase 6 (Completed - Authentication-first AI access)
1. Enforced login requirement for assistant usage endpoints (chat, legacy ask, TTS/session operations/report creation) at backend permission layer.
2. Updated floating assistant UI to show login-required state and CTA to Login.
3. Protected `/chat` route via app-level `ProtectedRoute` to keep AI interfaces authenticated end-to-end.

## 🚧 Phase 7 (Next - Define first AI response behavior)
1. Audit the current first-response source in assistant flows and document exact messages sent on first user message.
2. Standardize greeting by lane:
   - Marketplace FAQ lane.
   - Customer-service/dispute lane.
3. Add a configurable “first response template” for fast iteration without code rewrites.

## 🚧 Phase 8 (Improve Grok context and intelligence)
1. Improve context package quality sent to LLM:
   - User state (guest/logged in, role, recent activity).
   - Shopping intent signals (recent categories, viewed products, price band).
   - Retrieval evidence (top relevant FAQ/doc snippets with confidence).
2. Add heuristic personalization layer before LLM prompt:
   - “User viewed X, prefers Y, currently requests Z”.
3. Add structured product grounding:
   - Inject currently available matching products from DB with lightweight ranking.
4. Improve response quality controls:
   - Confidence gating.
   - Safe fallback when retrieval confidence is low.
   - Clarifying questions when intent is ambiguous.

## Data needed from you (for fastest progress)
- Brand assets: hero banners, campaign graphics, promo text options.
- Trust metrics for social proof: e.g., verified sellers count, delivery coverage, support SLA.
- Priority category order and fallback category imagery.
- Which homepage modules should be visible during testing when product count is low.
- For Phase 8: ranking preferences (price, location, freshness, seller rating) for AI product suggestions.
