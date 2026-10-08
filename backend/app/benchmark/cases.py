"""Labelled messages for the accuracy benchmark. 'scam' cases should be flagged (suspicious / likely scam);
'genuine' cases should NOT be flagged. Names of genuine employers are used only to test the pipeline.

CASES is the development set: the scoring rules were tuned while looking at it, so its accuracy is optimistic.
HOLDOUT was written on Oct 8, 2026 after the rules were frozen and is never tuned against. Scam texts follow
patterns from 2026 Indian police and news reports; genuine ones are real postings or real company domains."""
CASES = [
    # ---- scams ----
    {"id": "s1", "label": "Fake internship, fee on UPI", "expected": "scam",
     "text": "Congratulations! You are selected for Software Development Intern at Zentrix Global Solutions Pvt Ltd, Bengaluru. Stipend ₹25,000/month, no interview needed. Pay a refundable registration fee of ₹1,999 via UPI within 24 hours. Contact HR zentrix.hr2024@gmail.com"},
    {"id": "s2", "label": "Infosys name, off-domain recruiter", "expected": "scam",
     "text": "Dear candidate, we are pleased to offer you Systems Engineer Trainee at Infosys Limited, Bengaluru. Send a security deposit of ₹4,500 to proceed. Contact: hr.recruitment@infosys-careers.co.in"},
    {"id": "s3", "label": "iPhone at ₹9,999", "expected": "scam",
     "text": "MEGA SALE! iPhone 15 128GB only ₹9,999 (MRP ₹1,29,900). Limited stock, only 3 left! Pay via UPI to confirm, delivery in 2 days. WhatsApp us: +91 9123456780"},
    {"id": "s4", "label": "Like-videos job, Telegram, daily pay", "expected": "scam",
     "text": "Part time work from home! Earn ₹5000 per day just liking videos. No experience, no interview. Join our Telegram group, pay ₹500 registration to activate your account. Limited seats, hurry!"},
    {"id": "s5", "label": "TCS offer from Gmail with deposit", "expected": "scam",
     "text": "Offer letter: Assistant System Engineer at Tata Consultancy Services, Pune. Selected directly without exam. Pay ₹3,000 onboarding fee to tcs.hrdept.offers@gmail.com within 24 hours to confirm joining."},
    {"id": "s6", "label": "Wipro recruiter asks for kit fee", "expected": "scam",
     "text": "Hello, Wipro Limited is hiring freshers for Project Engineer in Hyderabad. 100% placement guarantee. Pay training kit charges ₹2,500 via PhonePe to reserve your seat. Contact wipro.jobs.india@outlook.com"},
    {"id": "s7", "label": "Smart TV at 90% off", "expected": "scam",
     "text": "Diwali dhamaka! Samsung 55 inch 4K Smart TV only ₹4,999 (MRP ₹79,990). Only 2 pieces left. Pay advance on UPI to book. WhatsApp +91 9000011122"},
    {"id": "s8", "label": "Lottery / KBC style prize", "expected": "scam",
     "text": "Congratulations! You have won ₹25,00,000 in the KBC lucky draw. To claim your prize pay processing fee ₹4,999 via Google Pay immediately. Contact on WhatsApp only. Offer expires within 2 hours."},
    # ---- scams with NO payment demand: text rules alone cannot see these ----
    {"id": "s9", "label": "Infosys look-alike domain, asks for documents", "expected": "scam",
     "text": "Dear Candidate, congratulations on clearing the screening for Systems Engineer at Infosys Limited, Mysuru. Your onboarding documentation is being processed. Please reply with scanned copies of your Aadhaar, PAN and bank passbook so we can issue your offer letter. Regards, Talent Acquisition, onboarding@infosys-hrdesk.in"},
    {"id": "s10", "label": "TCS interview from look-alike domain", "expected": "scam",
     "text": "Greetings from Tata Consultancy Services. You are shortlisted for the Digital profile in Chennai. Your virtual interview is scheduled for Monday 11 AM. Kindly confirm your availability by replying to talent@tcs-careerhub.co.in"},
    {"id": "s11", "label": "Company that does not exist", "expected": "scam",
     "text": "Hi, this is Meera from Nexvora Techlabs Pvt Ltd, Pune. You have been shortlisted for Associate Software Engineer, CTC 6.5 LPA. Please complete the joining formalities this week. Reply to hr@nexvoratechlabs.in for your offer letter."},
    {"id": "s12", "label": "Task scam using a real brand, no fee yet", "expected": "scam",
     "text": "Hi! I'm Riya from the Amazon partner team. We are hiring part-time to rate hotels on Google Maps, earn ₹3,000-₹8,000 daily from your phone. Interested? Reply YES and I will add you on Telegram."},
    # ---- genuine ----
    {"id": "g1", "label": "Infosys careers page announcement", "expected": "genuine",
     "text": "Infosys is hiring Systems Engineers in Bengaluru. Apply on the official careers page infosys.com/careers. Interviews are conducted online by invitation from careers@infosys.com. No fee is charged at any stage."},
    {"id": "g2", "label": "TCS NQT notification", "expected": "genuine",
     "text": "Tata Consultancy Services invites final-year students to register for the TCS NQT hiring test at nextstep.tcs.com. Registration details and the test schedule are on the official TCS website."},
    {"id": "g3", "label": "Zoho developer opening", "expected": "genuine",
     "text": "Zoho Corporation has openings for Member Technical Staff in Chennai. Apply through zoho.com/careers. Selection is via online tests and interviews. Questions? careers@zohocorp.com."},
    {"id": "g4", "label": "Razorpay backend intern", "expected": "genuine",
     "text": "Razorpay is hiring Backend Engineering Interns in Bengaluru, stipend ₹40,000/month. Apply at razorpay.com/jobs. Interview process: coding round and two technical interviews. No fees."},
    {"id": "g5", "label": "Wipro careers drive", "expected": "genuine",
     "text": "Wipro Limited is hiring Project Engineers in Hyderabad. Apply at careers.wipro.com and attend the online assessment. Official communication will come from wipro.com email addresses only."},
    # recruiter-style messages as people actually receive them: no "no fee" reassurance, some urgency
    {"id": "g8", "label": "Freshworks recruiter schedules a round", "expected": "genuine",
     "text": "Hi Arjun, this is Priya from the Freshworks talent team. Thanks for applying to the Software Engineer role in Chennai. Can we schedule your first technical round this Thursday? Reply with a slot that works. priya.s@freshworks.com"},
    {"id": "g9", "label": "Zerodha assignment email", "expected": "genuine",
     "text": "Zerodha is hiring a Frontend Developer (React) in Bengaluru. Shortlisted candidates will get a take-home assignment from careers@zerodha.com. Submit it within 3 days."},
    {"id": "g10", "label": "Postman intern next stage", "expected": "genuine",
     "text": "Hey! Your application for the Software Engineer Intern role at Postman, Bengaluru has moved to the next stage. Please pick an interview slot from the scheduling link we sent. Postman Talent Team, recruiting@postman.com"},
    {"id": "g11", "label": "Swiggy drive, confirm by tonight", "expected": "genuine",
     "text": "Swiggy campus hiring: final round interviews for SDE-1 are on Friday at our Bengaluru office. Please confirm attendance by tonight. Questions: campus@swiggy.in"},
    {"id": "g6", "label": "Flipkart phone at market price", "expected": "genuine",
     "text": "Samsung Galaxy M35 5G 6GB 128GB available at ₹17,499 on Flipkart with bank offers. Cash on delivery available."},
    {"id": "g7", "label": "Redmi at near-MRP", "expected": "genuine",
     "text": "Redmi Note 13 5G 8GB 128GB now ₹15,999 (MRP ₹18,999) on mi.com during the sale. Delivery in 3-5 days."},
]

HOLDOUT = [
    # ---- scams (patterns from 2026 police / news reports) ----
    {"id": "h-s1", "label": "Food-review task job on WhatsApp", "expected": "scam",
     "text": "Hello, I am Neha from a digital marketing agency. We have part-time work from your phone: post food reviews for restaurants and get paid ₹5,000 to ₹8,650 per day. Tasks are given on Telegram. Reply 'YES' to start today."},
    {"id": "h-s2", "label": "'HR executive' asks refundable registration fee", "expected": "scam",
     "text": "This is Rohit from HR, Tech Mahindra. You have been selected for Customer Support Executive in Noida. Please pay ₹2,500 registration and account opening charges, fully refunded after joining. Send the screenshot to techmahindra.hr.noida@gmail.com"},
    {"id": "h-s3", "label": "Deloitte offer letter from look-alike domain, no fee", "expected": "scam",
     "text": "Dear Applicant, please find attached your offer letter for Analyst at Deloitte, Hyderabad. Kindly sign it and share your Aadhaar, PAN and last three months' bank statements to complete background verification. Regards, Talent Team, careers@deloitte-india-hr.com"},
    {"id": "h-s4", "label": "Fake placement agency with processing fee", "expected": "scam",
     "text": "Velorix Staffing Solutions, Bhubaneswar: 100% guaranteed job in Amazon warehouse, salary ₹22,000. No interview. Pay ₹3,500 processing fee on PhonePe to book your joining date. Reply on WhatsApp to this number."},
    {"id": "h-s5", "label": "Wipro interview from look-alike domain, no fee", "expected": "scam",
     "text": "Greetings from Wipro Limited. Your profile is shortlisted for Associate Engineer, Bengaluru. Please join the virtual HR discussion tomorrow at 10 AM and confirm by replying to hiring@wipro-talentdesk.in"},
    # ---- genuine ----
    {"id": "h-g1", "label": "Real Accenture posting (LinkedIn link)", "expected": "genuine",
     "text": "https://www.linkedin.com/jobs/view/4474509677/"},
    {"id": "h-g2", "label": "Real Wahed posting (Lever link)", "expected": "genuine",
     "text": "https://jobs.lever.co/wahed.com/479cd76f-d0b5-47e5-86f0-7f8f18605bf1?lever-source=Indeed"},
    {"id": "h-g3", "label": "Groww recruiter email", "expected": "genuine",
     "text": "Hi, this is Aditi from the Groww talent acquisition team. We'd like to move your application for SDE-2 (Backend), Bengaluru to the technical round. Please share your availability for next week. aditi.r@groww.in"},
    {"id": "h-g4", "label": "Meesho campus interview", "expected": "genuine",
     "text": "Hello from Meesho! You have been shortlisted for the Software Development Engineer role in Bengaluru. The online coding assessment link will be sent from campus@meesho.com within two days."},
    {"id": "h-g5", "label": "CRED hiring manager reply", "expected": "genuine",
     "text": "Thanks for applying to CRED for the Android Engineer role in Bengaluru. Our hiring manager would like a 30-minute intro call this Friday. Please reply with a convenient time. careers@cred.club"},
    {"id": "h-g6", "label": "Juspay assignment", "expected": "genuine",
     "text": "Juspay Technologies: thank you for your interest in the Product Engineer role, Bengaluru. Please complete the attached take-home assignment within 5 days and reply to talent@juspay.in"},
]
