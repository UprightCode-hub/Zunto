#server/assistant/ai/creator_info.py
"""Creator and team profile data used for attribution responses."""
from typing import Dict, List, Optional
from datetime import datetime


class CreatorInfo:
    """
    Complete information about the creator and development team.
    """
    
                                    
    CREATOR = {
        'name': 'Wisdom Ekwugha',
        'role': 'AI Systems Developer & Creator of Gigi',
        'title': 'Lead AI Engineer',
        
                                                                          
        'background': {
            'education': 'Self-taught AI & Software Developer; currently a university student',
            'experience_years': '2 years',
            'location': 'Nigeria',
            'specializations': [
                'AI & Machine Learning',
                'Natural Language Processing',
                'Backend Development (Python & Django)',
                'Conversational AI',
                'RAG Systems & Vector Search'
            ],
        },
        
        'professional': {
            'current_role': 'AI Engineer, Python/Django Developer & Founder of GDE (Gigi Development Engine)',
            'company': 'Zunto Team',
            'previous_projects': [
                'Gigi — Zunto\'s AI Assistant: full conversational system with rule engine, RAG pipeline, and LLM orchestration',
                'Custom RAG Pipeline (FAISS + embeddings + multi-stage confidence scoring)',
                'Banking Dashboard CLI System (Python)',
                'Django Marketplace Chat Module (secure buyer–seller chat, API endpoints)',
                'CSV/Data Cleaning Automation Scripts'
            ],
            'achievements': [
                'Developed a fully local conversational AI stack before age 18, including rule–matching and retrieval orchestration',
                'Founded GDE (Gigi Development Engine), the framework powering Zunto\'s assistant',
                'Built an end-to-end RAG system focusing on cost-efficiency and performance',
                'Self-taught AI engineer through YouTube resources and AI-assisted learning'
            ],
        },
        
        'zunto_project': {
            'started': 'May 2025',
            'inspiration': (
                "To create an intelligent assistant that understands Nigerian "
                "and African e-commerce needs, providing instant, accurate support "
                "while reducing operational costs for marketplace platforms."
            ),
            'vision': (
                "Build Africa's most intelligent marketplace assistant, capable of handling complex disputes, multilingual support, "
                "and providing human-like customer service at scale."
            ),
            'technologies_used': [
                'Django 5.1',
                'FAISS (Vector Search)',
                'GPT4All (Local LLM)',
                'BGE Embeddings',
                'Sentence-Transformers',
                'PostgreSQL',
                'React (Frontend)',
                'Python 3.12',
                'Docker',
                'Celery',
                'Redis',
                'Custom Rule Engine',
                'Custom Query Processor',
            ],
        },
        
        'contact': {
            'linkedin': None,
            'github': None,
            'twitter': None,
            'email': None,
            'portfolio': None,
        },
        
        'personal': {
            'interests': [
                'Artificial Intelligence',
                'Machine Learning',
                'Software Architecture',
                'Data Analysis',
                'E-commerce Systems'
            ],
            'philosophy': (
                "Building AI systems that genuinely help people, not just impress with complexity."
            ),
        },
        
                                      
        'tone_guidelines': {
            'preferred_tone': 'professional_humble',                                               
            'emphasis': [
                'Technical expertise in AI/ML',
                'Focus on practical solutions',
                'Commitment to African tech ecosystem',
            ],
            'avoid': [
                'Overly boastful language',
                'Technical jargon when explaining to users',
            ]
        }
    }
    
                      
    TEAM = {
        'name': 'Zunto Team',
        'role': 'Marketplace Platform Developers',
        'description': (
            "The Zunto Team is responsible for building and maintaining "
            "the Zunto Marketplace platform - Nigeria's innovative e-commerce solution. "
            "While the team handles the marketplace infrastructure, Wisdom Ekwugha "
            "specifically created and developed Gigi, the AI assistant."
        ),
        'division_of_work': {
            'marketplace_platform': 'Zunto Team (Frontend, Backend, Infrastructure)',
            'ai_assistant': 'Wisdom Ekwugha (Design, Development, Training)',
        }
    }
    
                                       
    TIMELINE = {
        'project_start': datetime(2025, 5, 1),            
        'ai_development_start': datetime(2025, 9, 1),                  
        'first_version_deployed': datetime(2025, 12, 1),                                         
        'current_version': '2.0',
        'milestones': [
            {'date': datetime(2025, 5, 1), 'event': 'Project concept & planning (Zunto)'},
            {'date': datetime(2025, 7, 15), 'event': 'MVP backend prototype (Django + Postgres)'},
            {'date': datetime(2025, 9, 1), 'event': 'AI development begins (Gigi prototype)'} ,
            {'date': datetime(2025, 10, 10), 'event': 'Hybrid RAG pipeline implemented (FAISS + embeddings)'},
            {'date': datetime(2025, 11, 12), 'event': 'Private beta: Marketplace chat integration & rule engine testing'},
            {'date': datetime(2025, 12, 1), 'event': 'First production test and live validation'},
        ]
    }
    
                                 
    FUN_FACTS = [
        "Gigi can process 346 FAQs in under 0.04 seconds!",
        "The name 'Gigi' was chosen to be friendly and memorable.",
        "Gigi saves 65% in API costs using smart 3-tier confidence system.",
        "Wisdom built Gigi's name detection to handle over 20 cultural name patterns.",
    ]
    
    @classmethod
    def get_creator_bio(cls, detail_level: str = 'balanced') -> str:
        """
        Generate creator biography at different detail levels.
        
        Args:
            detail_level: 'brief', 'balanced', or 'detailed'
        """
        creator = cls.CREATOR
        
        if detail_level == 'brief':
            return (
                f"{creator['name']} is the creator and lead developer of Gigi, "
                f"Zunto Marketplace's AI assistant. He specializes in AI systems "
                f"and conversational AI, bringing intelligent automation to "
                f"African e-commerce."
            )
        
        elif detail_level == 'detailed':
            bg = creator['background']
            proj = creator['zunto_project']
            
            return (
                f"{creator['name']} is a {bg.get('experience_years', 'seasoned')} "
                f"AI systems developer based in {bg['location']}. He created Gigi, "
                f"the intelligent assistant powering Zunto Marketplace.\n\n"
                f"With expertise in {', '.join(bg['specializations'][:3])}, Wisdom "
                f"designed Gigi to understand the unique needs of African e-commerce. "
                f"His vision: {proj['vision']}\n\n"
                f"The inspiration behind Gigi came from {proj['inspiration']}\n\n"
                f"Technical stack: {', '.join(proj['technologies_used'][:7])}."
            )
        
        else:            
            return (
                f"{creator['name']} is the creator of Gigi, Zunto's AI assistant. "
                f"As an AI systems developer specializing in conversational AI and "
                f"natural language processing, Wisdom built Gigi from the ground up "
                f"to provide intelligent, cost-effective customer support.\n\n"
                f"His vision is to build Africa's most intelligent marketplace "
                f"assistant, capable of handling complex queries while feeling "
                f"genuinely helpful and human."
            )
    
    @classmethod
    def get_team_info(cls) -> str:
        """Get info about Zunto Team."""
        team = cls.TEAM
        return (
            f"The {team['name']} develops the Zunto Marketplace platform. "
            f"{team['description']}"
        )
    
    @classmethod
    def get_attribution(cls) -> str:
        """Get proper attribution for 'who made you' questions."""
        return (
            f"I'm Gigi, created by {cls.CREATOR['name']}. "
            f"He's an AI systems developer who built me specifically for "
            f"Zunto Marketplace. The marketplace platform itself is developed "
            f"by the {cls.TEAM['name']}, but I'm Wisdom's creation! 😊"
        )
    
    @classmethod
    def get_fun_fact(cls) -> str:
        """Get random fun fact."""
        import random
        return random.choice(cls.FUN_FACTS)
    
    @classmethod
    def should_mention_creator(cls, user_query: str) -> bool:
        """
        Detect if user is asking about creator.
        
        Triggers:
        - "who made you"
        - "who created you"
        - "who developed you"
        - "tell me about your creator"
        - "who is wisdom"
        - etc.
        """
        query_lower = user_query.lower()
        
        creator_keywords = [
            'who made you',
            'who created you',
            'who developed you',
            'who built you',
            'your creator',
            'your developer',
            'who is wisdom',
            'wisdom Ekwugha',
            'tell me about wisdom',
            'who designed you',
            'your creator',
        ]
        
        return any(keyword in query_lower for keyword in creator_keywords)
    
    @classmethod
    def get_response_for_creator_query(cls, user_query: str, user_name: str = None) -> str:
        """
        Generate appropriate response when user asks about creator.
        
        Analyzes query to determine detail level needed.
        """
        query_lower = user_query.lower()
        
                                           
        if 'more about' in query_lower or 'tell me about' in query_lower or 'detailed' in query_lower:
            detail_level = 'detailed'
        elif 'briefly' in query_lower or 'quick' in query_lower or 'short' in query_lower:
            detail_level = 'brief'
        else:
            detail_level = 'balanced'
        
                           
        bio = cls.get_creator_bio(detail_level)
        
                                            
        if user_name:
            return f"{user_name}, {bio}"
        else:
            return bio
    
    @classmethod
    def update_creator_details(cls, updates: Dict):
        """
        Update creator details (for easy maintenance).
        
        Usage:
            CreatorInfo.update_creator_details({
                'background': {
                    'education': 'B.Sc Computer Science, University of Lagos'
                }
            })
        """
        for key, value in updates.items():
            if key in cls.CREATOR:
                if isinstance(value, dict) and isinstance(cls.CREATOR[key], dict):
                    cls.CREATOR[key].update(value)
                else:
                    cls.CREATOR[key] = value


                       
def get_creator_info(detail: str = 'balanced') -> str:
    """Quick access to creator bio."""
    return CreatorInfo.get_creator_bio(detail)


def is_asking_about_creator(query: str) -> bool:
    """Check if user is asking about creator."""
    return CreatorInfo.should_mention_creator(query)


def answer_creator_question(query: str, user_name: str = None) -> str:
    """Generate answer about creator."""
    return CreatorInfo.get_response_for_creator_query(query, user_name)


                             
                                                                                       
                                                                           

                     
contact_info = {
    "email": "ZuntoProject@gmail.com",
    "github": "https://github.com/UprightCode-hub"
}

                                                

                                                              
CREATOR_INFO = CreatorInfo.CREATOR


def get_creator_bio(detail_level: str = 'balanced', user_name: Optional[str] = None) -> str:
    """
    Get creator biography with optional personalization.
    
    Args:
        detail_level: 'brief', 'balanced', or 'detailed'
        user_name: Optional user name for personalization
    
    Returns:
        Formatted biography string
    
    Examples:
        >>> get_creator_bio('brief')
        'Wisdom Ekwugha is the creator and lead developer of Gigi...'
        
        >>> get_creator_bio('detailed', 'John')
        'John, Wisdom Ekwugha is a 2 years systems developer...'
    """
    bio = CreatorInfo.get_creator_bio(detail_level)
    
    if user_name:
        return f"{user_name}, {bio}"
    return bio


def format_creator_card() -> str:
    """
    Format creator information as a conversational card/introduction.
    
    Returns:
        Formatted string with creator attribution and quick facts
    
    Example Output:
        "I'm Gigi, created by Wisdom Ekwugha. He's a systems developer
        who built me specifically for Zunto Marketplace..."
    """
    attribution = CreatorInfo.get_attribution()
    fun_fact = CreatorInfo.get_fun_fact()
    
    return (
        f"{attribution}\n\n"
        f"💡 Fun fact: {fun_fact}"
    )


def get_detailed_creator_response(user_query: str, user_name: Optional[str] = None) -> str:
    """
    Generate a detailed response when users ask about the creator.
    
    This function analyzes the user's query and provides appropriate
    detail level and context.
    
    Args:
        user_query: User's question about the creator
        user_name: Optional user name for personalization
    
    Returns:
        Contextual response about Wisdom Ekwugha
    
    Examples:
        >>> get_detailed_creator_response("who made you?")
        'Wisdom Ekwugha is the creator of Gigi...'
        
        >>> get_detailed_creator_response("tell me more about wisdom", "Sarah")
        'Sarah, Wisdom Ekwugha is a 2 years systems developer...'
    """
    return CreatorInfo.get_response_for_creator_query(user_query, user_name)


def should_mention_creator(user_query: str) -> bool:
    """
    Detect if user is asking about the creator.
    
    Triggers on keywords like:
    - "who made you"
    - "who created you"
    - "tell me about your creator"
    - "who is wisdom"
    
    Args:
        user_query: User's message
    
    Returns:
        True if query is about the creator
    """
    return CreatorInfo.should_mention_creator(user_query)


                             

def get_team_info() -> str:
    """Get information about the Zunto development team."""
    return CreatorInfo.get_team_info()


def get_project_timeline() -> Dict:
    """Get project development timeline."""
    return CreatorInfo.TIMELINE


def get_technologies_used() -> List[str]:
    """Get list of technologies used in Gigi."""
    return CreatorInfo.CREATOR['zunto_project']['technologies_used']


def get_creator_achievements() -> List[str]:
    """Get list of creator's achievements."""
    return CreatorInfo.CREATOR['professional']['achievements']


def get_creator_contact() -> Dict:
    """Get creator contact information."""
    return {
        **CreatorInfo.CREATOR['contact'],
        'email': contact_info.get('email'),
        'github': contact_info.get('github')
    }
