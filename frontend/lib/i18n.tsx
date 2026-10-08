"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from "react";
import type { Verdict } from "./types";

export type Lang = "en" | "hi";

const en = {
  tagline: "Check before you trust",
  navBenchmark: "Accuracy",
  install: "Install app",
  heroA: "Is this offer",
  heroB: "real",
  heroC: "?",
  heroSub: "Paste the job offer, seller message, deal or link you received. TrustLens cross-checks it against live Google data and shows its working, so you can see why.",
  pasteLabel: "What did you receive?",
  pasteHelp: "A WhatsApp forward, offer letter, seller message, a deal, or just a link. English, Hindi or Hinglish.",
  pastePlaceholder: "Congratulations! You are selected for…   (or paste a link, or a screenshot with Ctrl+V)",
  examples: "Try a real-pattern example",
  screenshot: "Screenshot",
  screenshotHelp: "Drop or choose a WhatsApp screenshot. We read the text for you.",
  screenshotChange: "Remove",
  imageUrl: "Image URL for Lens check",
  investigate: "Investigate",
  stop: "Stop",
  privacy: "Messages are sent to Gemini and SerpApi for analysis. Don't paste OTPs or bank details.",
  emptyTitle: "No case open yet",
  emptyBody: "Pick an example or paste something suspicious. You will watch the agent plan, search and cross-examine its own sources.",
  extracted: "Extracted subject",
  unknownCompany: "Unknown company",
  verdictWord: "Verdict",
  confidence: { low: "low confidence", medium: "medium confidence", high: "high confidence" },
  scoreLabel: "Trust score",
  whatToDo: "What to do now",
  disagree: "Where the sources disagree",
  evidence: "Evidence trail",
  ledger: "How the score is built",
  ledgerBase: "Start",
  ledgerTotal: "Trust score",
  ledgerNote: "Fixed rules add or subtract points for each finding. The AI writes the explanation but never changes the score.",
  graph: "Evidence graph",
  graphHint: "Hover a node to trace it. Dashed red lines are contradictions.",
  warnFamily: "Warn your family group",
  copy: "Copy",
  copied: "Copied",
  whatsapp: "Send on WhatsApp",
  downloadCard: "Download card",
  share: "Share",
  liveCalls: (n: number, c: number) => `${n} live SerpApi call${n === 1 ? "" : "s"}, ${c} from cache`,
  engines: "Engines",
  apiDown: "Could not reach the TrustLens API. Is the backend running?",
  verdicts: {
    likely_genuine: { label: "Likely genuine", stamp: "LIKELY GENUINE", blurb: "Evidence supports this being real. Still verify through official channels." },
    verify: { label: "Verify first", stamp: "VERIFY FIRST", blurb: "Mixed or thin evidence. Confirm independently before acting." },
    suspicious: { label: "Suspicious", stamp: "SUSPICIOUS", blurb: "Several signals do not add up. Do not pay or share details." },
    likely_scam: { label: "Likely scam", stamp: "LIKELY SCAM", blurb: "Strong signs of fraud. Do not pay, click or reply." },
  } as Record<Verdict, { label: string; stamp: string; blurb: string }>,
  helpline: "Report cyber fraud: call 1930 or visit cybercrime.gov.in",
  footerA: "Evidence from live Google data via SerpApi (Search, News, Maps, Jobs, Shopping, Lens). Explanations written by Gemini. Built with Claude Code.",
  footerB: "TrustLens gives guidance, not legal advice. Always confirm through the organisation's official channel.",
  // benchmark
  bmTitle: "How accurate is it?",
  bmSub: "TrustLens was run on labelled real-pattern messages, scams and genuine offers alike. Same pipeline, live Google data, no tuning per message.",
  bmCaught: "Scams flagged",
  bmCleared: "Genuine not flagged",
  bmOverall: "Overall",
  bmMsg: "Message",
  bmExpected: "Truth",
  bmGot: "TrustLens said",
  bmScore: "Score",
  bmScam: "Scam",
  bmGenuine: "Genuine",
  bmEmpty: "No benchmark has been generated yet.",
  bmMethod: "A scam counts as caught when the verdict is Suspicious or Likely scam. A genuine message counts as cleared when it is not flagged. Misses are shown, not hidden.",
  bmAblTitle: "What live search adds",
  bmAblSub: "Every message was also scored with the offline text rules alone (fee demands, urgency, chat-app pressure), i.e. TrustLens without SerpApi.",
  bmAblText: "Text rules only",
  bmAblFull: "With SerpApi evidence",
  bmTextOnly: "Text only",
  bmHoldTitle: "On messages it was never tuned on",
  bmHoldSub: "Written after the scoring rules were frozen (and committed to git before being run): scam patterns from 2026 Indian police and news reports, plus real job postings and real company recruiters. This is the honest number.",
  bmDevTitle: "Development set",
  bmDevSub: "The rules were tuned while looking at these, so this score is optimistic.",
  bmUnseen: "unseen",
  back: "Back to checker",
  // share
  shareHeading: "TrustLens check",
  shareFoot: "Checked with TrustLens · live Google data via SerpApi",
};

type Dict = typeof en;

const hi: Dict = {
  tagline: "भरोसा करने से पहले जाँचें",
  navBenchmark: "सटीकता",
  install: "ऐप इंस्टॉल करें",
  heroA: "क्या यह ऑफ़र",
  heroB: "सच्चा",
  heroC: " है?",
  heroSub: "जो जॉब ऑफ़र, विक्रेता का संदेश, डील या लिंक आपको मिला है, उसे यहाँ चिपकाएँ। TrustLens उसे लाइव Google डेटा से मिलाकर जाँचता है और वजह भी दिखाता है।",
  pasteLabel: "आपको क्या मिला?",
  pasteHelp: "WhatsApp फ़ॉरवर्ड, ऑफ़र लेटर, विक्रेता का संदेश, कोई डील, या सिर्फ़ एक लिंक। हिंदी, अंग्रेज़ी या हिंग्लिश।",
  pastePlaceholder: "बधाई हो! आपका चयन हुआ है…   (या लिंक चिपकाएँ, या Ctrl+V से स्क्रीनशॉट)",
  examples: "एक उदाहरण आज़माएँ",
  screenshot: "स्क्रीनशॉट",
  screenshotHelp: "WhatsApp स्क्रीनशॉट चुनें या यहाँ छोड़ें। हम उसका लिखा पढ़ लेंगे।",
  screenshotChange: "हटाएँ",
  imageUrl: "Lens जाँच के लिए इमेज URL",
  investigate: "जाँच शुरू करें",
  stop: "रोकें",
  privacy: "संदेश विश्लेषण के लिए Gemini और SerpApi को भेजे जाते हैं। OTP या बैंक की जानकारी न चिपकाएँ।",
  emptyTitle: "अभी कोई केस खुला नहीं है",
  emptyBody: "कोई उदाहरण चुनें या संदिग्ध संदेश चिपकाएँ। आप देखेंगे कि एजेंट कैसे योजना बनाता है, खोजता है और अपने ही स्रोतों की जाँच करता है।",
  extracted: "पहचाना गया विषय",
  unknownCompany: "अज्ञात कंपनी",
  verdictWord: "निर्णय",
  confidence: { low: "कम भरोसा", medium: "मध्यम भरोसा", high: "ज़्यादा भरोसा" },
  scoreLabel: "ट्रस्ट स्कोर",
  whatToDo: "अब क्या करें",
  disagree: "जहाँ स्रोत आपस में मेल नहीं खाते",
  evidence: "साक्ष्य सूची",
  ledger: "स्कोर कैसे बना",
  ledgerBase: "शुरुआत",
  ledgerTotal: "ट्रस्ट स्कोर",
  ledgerNote: "हर पाए गए तथ्य पर तय नियमों से अंक जुड़ते या घटते हैं। AI सिर्फ़ व्याख्या लिखता है, स्कोर कभी नहीं बदलता।",
  graph: "साक्ष्य ग्राफ़",
  graphHint: "किसी बिंदु पर माउस ले जाएँ। लाल बिंदीदार रेखाएँ विरोधाभास दिखाती हैं।",
  warnFamily: "अपने परिवार के ग्रुप को सावधान करें",
  copy: "कॉपी करें",
  copied: "कॉपी हो गया",
  whatsapp: "WhatsApp पर भेजें",
  downloadCard: "कार्ड डाउनलोड करें",
  share: "शेयर करें",
  liveCalls: (n: number, c: number) => `${n} लाइव SerpApi कॉल, ${c} कैश से`,
  engines: "इंजन",
  apiDown: "TrustLens API से संपर्क नहीं हो सका। क्या बैकएंड चालू है?",
  verdicts: {
    likely_genuine: { label: "संभवतः असली", stamp: "संभवतः असली", blurb: "साक्ष्य इसके असली होने का समर्थन करते हैं। फिर भी आधिकारिक माध्यम से पुष्टि करें।" },
    verify: { label: "पहले जाँच लें", stamp: "पहले जाँच लें", blurb: "साक्ष्य मिले-जुले या कम हैं। कदम उठाने से पहले खुद पुष्टि करें।" },
    suspicious: { label: "संदिग्ध", stamp: "संदिग्ध", blurb: "कई संकेत मेल नहीं खाते। पैसे न दें और जानकारी साझा न करें।" },
    likely_scam: { label: "धोखाधड़ी लगती है", stamp: "स्कैम!", blurb: "धोखाधड़ी के मज़बूत संकेत हैं। पैसे न दें, क्लिक न करें, जवाब न दें।" },
  },
  helpline: "साइबर धोखाधड़ी की शिकायत: 1930 पर कॉल करें या cybercrime.gov.in पर जाएँ",
  footerA: "साक्ष्य लाइव Google डेटा से, SerpApi के ज़रिए (Search, News, Maps, Jobs, Shopping, Lens)। व्याख्या Gemini ने लिखी। Claude Code से बनाया गया।",
  footerB: "TrustLens मार्गदर्शन देता है, कानूनी सलाह नहीं। हमेशा संस्था के आधिकारिक माध्यम से पुष्टि करें।",
  bmTitle: "यह कितना सटीक है?",
  bmSub: "TrustLens को असली जैसे संदेशों पर चलाया गया, स्कैम और असली दोनों। वही पाइपलाइन, लाइव Google डेटा, हर संदेश के लिए अलग ट्यूनिंग नहीं।",
  bmCaught: "पकड़े गए स्कैम",
  bmCleared: "असली, जिन्हें गलत नहीं पकड़ा",
  bmOverall: "कुल",
  bmMsg: "संदेश",
  bmExpected: "सच्चाई",
  bmGot: "TrustLens का निर्णय",
  bmScore: "स्कोर",
  bmScam: "स्कैम",
  bmGenuine: "असली",
  bmEmpty: "अभी कोई बेंचमार्क नहीं बना है।",
  bmMethod: "निर्णय 'संदिग्ध' या 'स्कैम' हो तो स्कैम पकड़ा गया माना जाता है। असली संदेश को तब सही माना जाता है जब उसे गलत न पकड़ा जाए। चूक भी दिखाई जाती हैं, छिपाई नहीं जातीं।",
  bmAblTitle: "लाइव सर्च से क्या फ़र्क पड़ता है",
  bmAblSub: "हर संदेश को सिर्फ़ ऑफ़लाइन टेक्स्ट नियमों (फ़ीस की माँग, जल्दबाज़ी, चैट-ऐप का दबाव) से भी जाँचा गया, यानी SerpApi के बिना TrustLens।",
  bmAblText: "सिर्फ़ टेक्स्ट नियम",
  bmAblFull: "SerpApi सबूत के साथ",
  bmTextOnly: "सिर्फ़ टेक्स्ट",
  bmHoldTitle: "उन संदेशों पर जिन पर इसे कभी ट्यून नहीं किया गया",
  bmHoldSub: "स्कोरिंग नियम तय होने के बाद लिखे गए (और चलाने से पहले git में दर्ज): 2026 की भारतीय पुलिस और समाचार रिपोर्टों के स्कैम पैटर्न, साथ में असली नौकरी पोस्टिंग और असली कंपनियों के रिक्रूटर। यही ईमानदार आँकड़ा है।",
  bmDevTitle: "डेवलपमेंट सेट",
  bmDevSub: "नियम इन्हीं को देखते हुए बनाए गए, इसलिए यह स्कोर आशावादी है।",
  bmUnseen: "अनदेखा",
  back: "जाँचकर्ता पर वापस",
  shareHeading: "TrustLens जाँच",
  shareFoot: "TrustLens से जाँचा · SerpApi के ज़रिए लाइव Google डेटा",
};

export const DICT: Record<Lang, Dict> = { en, hi };

interface Ctx { lang: Lang; setLang: (l: Lang) => void; t: Dict }
const LangCtx = createContext<Ctx>({ lang: "en", setLang: () => {}, t: en });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("tl-lang") as Lang | null;
      if (saved === "en" || saved === "hi") setLangState(saved);
      else if (navigator.language?.toLowerCase().startsWith("hi")) setLangState("hi");
    } catch {}
  }, []);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("tl-lang", l); } catch {}
  }, []);

  const value = useMemo(() => ({ lang, setLang, t: DICT[lang] }), [lang, setLang]);
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}

export const useLang = () => useContext(LangCtx);
