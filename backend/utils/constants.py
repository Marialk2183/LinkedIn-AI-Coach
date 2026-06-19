"""Domain taxonomies: skills, technical skills, role definitions, section headers."""

# Canonical skills the parser/scorer recognizes (lowercased on match).
TECHNICAL_SKILLS: set[str] = {
    "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust", "scala", "r",
    "sql", "nosql", "postgresql", "mysql", "mongodb", "redis",
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "nlp", "computer vision", "data science",
    "data analysis", "data visualization", "statistics", "tableau", "power bi", "excel",
    "spark", "hadoop", "airflow", "etl", "data engineering", "big data",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "linux",
    "react", "node.js", "fastapi", "django", "flask", "rest api", "graphql",
    "git", "html", "css", "matplotlib", "seaborn", "opencv", "transformers", "llm",
}

SOFT_SKILLS: set[str] = {
    "leadership", "communication", "teamwork", "problem solving", "project management",
    "stakeholder management", "agile", "scrum", "collaboration", "mentoring",
}

ALL_SKILLS: set[str] = TECHNICAL_SKILLS | SOFT_SKILLS

# Roles for the career-prediction module. Weighted core + nice-to-have skills.
ROLE_DEFINITIONS: dict[str, dict[str, list[str]]] = {
    "Data Scientist": {
        "core": ["python", "machine learning", "statistics", "pandas", "scikit-learn", "sql"],
        "nice": ["deep learning", "nlp", "tensorflow", "pytorch", "data visualization"],
    },
    "Data Analyst": {
        "core": ["sql", "excel", "data analysis", "data visualization", "statistics"],
        "nice": ["python", "tableau", "power bi", "pandas"],
    },
    "AI Engineer": {
        "core": ["python", "deep learning", "tensorflow", "pytorch", "machine learning"],
        "nice": ["nlp", "computer vision", "transformers", "llm", "docker"],
    },
    "Software Developer": {
        "core": ["java", "python", "javascript", "git", "rest api"],
        "nice": ["react", "node.js", "docker", "sql", "typescript"],
    },
    "Business Analyst": {
        "core": ["data analysis", "excel", "sql", "communication", "stakeholder management"],
        "nice": ["power bi", "tableau", "agile", "project management"],
    },
    "ML Engineer": {
        "core": ["python", "machine learning", "docker", "sql", "scikit-learn"],
        "nice": ["kubernetes", "aws", "airflow", "pytorch", "tensorflow", "ci/cd"],
    },
}

# Strong resume/profile action verbs — a density signal for achievement-oriented writing.
ACTION_VERBS: set[str] = {
    "led", "built", "designed", "developed", "created", "launched", "delivered",
    "implemented", "architected", "managed", "drove", "improved", "increased",
    "reduced", "optimized", "automated", "scaled", "shipped", "spearheaded",
    "owned", "mentored", "founded", "established", "engineered", "deployed",
    "analyzed", "researched", "produced", "achieved", "boosted", "accelerated",
    "streamlined", "transformed", "pioneered", "orchestrated", "generated",
}

# Recognized, role-relevant certifications recruiters value — used to make the
# "earn a certification" recommendation concrete instead of generic.
ROLE_CERTIFICATIONS: dict[str, list[str]] = {
    "Data Scientist": ["Google Data Analytics", "AWS Certified Machine Learning", "TensorFlow Developer"],
    "Data Analyst": ["Google Data Analytics", "Microsoft Power BI Data Analyst (PL-300)", "Tableau Desktop Specialist"],
    "AI Engineer": ["TensorFlow Developer", "AWS Certified Machine Learning", "DeepLearning.AI Deep Learning"],
    "Software Developer": ["AWS Certified Developer – Associate", "Oracle Certified Java Programmer", "Meta Front-End Developer"],
    "Business Analyst": ["IIBA ECBA", "Microsoft Power BI Data Analyst (PL-300)", "PMI-PBA"],
    "ML Engineer": ["AWS Certified Machine Learning", "Google Professional ML Engineer", "TensorFlow Developer"],
}

# Role/seniority keywords recruiters search for in a headline.
ROLE_KEYWORDS: set[str] = {
    "engineer", "developer", "scientist", "analyst", "manager", "lead", "architect",
    "consultant", "specialist", "designer", "researcher", "intern", "senior",
    "junior", "principal", "staff", "head", "director", "founder", "data",
    "software", "machine learning", "ml", "ai", "full stack", "fullstack",
    "backend", "frontend", "devops", "product",
}

# Section headers recognized in pasted profile text (case-insensitive).
SECTION_ALIASES: dict[str, list[str]] = {
    "about": ["about", "summary"],
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "education": ["education"],
    "certifications": ["certifications", "licenses & certifications", "licenses and certifications", "courses"],
    "projects": ["projects", "personal projects", "academic projects"],
    "skills": ["skills", "top skills", "skills & endorsements"],
}
