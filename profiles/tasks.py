import re

import httpx
import requests
from django.conf import settings
from django.core.mail import EmailMessage
from django_q.tasks import async_task

from profiles.agents import profile_analyzer_agent
from talentleads.utils import get_talentleads_logger, run_agent_synchronously

from profiles.models import Profile, Technology
from profiles.utils import clean_profile_json_object

logger = get_talentleads_logger(__name__)


def get_jina_embedding(text):
    """Get embedding from Jina API for the given text."""
    url = "https://api.jina.ai/v1/embeddings"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.JINA_API_KEY}"}
    data = {"model": "jina-embeddings-v3", "task": "text-matching", "input": [text]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        result = response.json()

        # Extract the embedding from the first result
        if result.get("data") and len(result["data"]) > 0:
            embedding = result["data"][0]["embedding"]
            logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
            return embedding
        else:
            logger.error(f"Unexpected response format from Jina API: {result}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting embedding from Jina API: {e}")
        return None


def get_hn_pages_to_analyze(who_wants_to_be_hired_post_id):
    data = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{who_wants_to_be_hired_post_id}.json").json()

    if "Who wants to be hired" not in data["title"]:
        return "Not a Who wants to be hired"

    list_of_comment_ids = data["kids"]

    # if working in dev don't want to go through all the comments
    if settings.DEBUG:
        list_of_comment_ids = list_of_comment_ids[:20]

    count = 0
    for comment_id in list_of_comment_ids:
        if not Profile.objects.filter(who_wants_to_be_hired_comment_id=comment_id).exists():
            async_task(
                analyze_hn_page,
                int(data["id"]),
                str(re.search(r"\(([^)]+)", data["title"]).group(1)),
                comment_id,
                hook="profiles.hooks.print_result",
                group="Analyze HN Page",
            )
            count += 1
        else:
            logger.info(f"Profile for {comment_id} already exists.")

    return f"{count} have been sent to be analyzed."


def analyze_hn_page(who_wants_to_be_hired_id, who_wants_to_be_hired_title, comment_id):
    logger.info(f"Analyzing comment {comment_id}")
    json_profile = httpx.get(f"https://hacker-news.firebaseio.com/v0/item/{comment_id}.json").json()

    try:
        if json_profile["deleted"] is True:
            return "Comment was deleted"
    except KeyError:
        pass

    who_wants_to_be_hired_comment_id = int(json_profile["id"])
    hn_username = str(json_profile["by"])

    result = run_agent_synchronously(
        profile_analyzer_agent,
        "Analyze the following profile and provide a detailed analysis of the profile.",
        deps=json_profile["text"],
        function_name="analyze_hn_page",
    )

    data = result.output.__dict__

    cleaned_data = clean_profile_json_object(json_profile, data)

    technology_names = cleaned_data["technologies_used"]
    technologies = []
    for name in technology_names:
        if name != "":
            obj, _ = Technology.objects.get_or_create(name=name)
            technologies.append(obj)

    # Generate embedding from the profile description
    embedding = get_jina_embedding(json_profile["text"])

    profile = Profile(
        latest_who_wants_to_be_hired_id=who_wants_to_be_hired_id,
        who_wants_to_be_hired_title=who_wants_to_be_hired_title,
        who_wants_to_be_hired_comment_id=who_wants_to_be_hired_comment_id,
        title=cleaned_data["title"],
        name=cleaned_data["name"],
        hn_username=hn_username,
        description=cleaned_data["description"],
        location=cleaned_data["location"],
        city=cleaned_data["city"],
        country=cleaned_data["country"],
        state=cleaned_data["state"],
        level=cleaned_data["level"],
        is_remote=cleaned_data["is_remote"],
        willing_to_relocate=cleaned_data["willing_to_relocate"],
        resume_link=cleaned_data["resume_link"],
        personal_website=cleaned_data["personal_website"],
        email=cleaned_data["email"],
        years_of_experience=cleaned_data["years_of_experience"],
        capacity=cleaned_data["capacity"],
        embedding=embedding,
    )
    profile.save()
    profile.tech_stack.add(*technologies)

    logger.info(f"{profile} profile was created.")

    return f"Comment {comment_id} Saved"


# Schedule.objects.create(
#     func=analyze_hn_page,
#     args=34983765,
#     hook="profiles.hooks.print_result",
#     schedule_type=Schedule.CRON,
#     cron = '0 0 * * *'
# )


def send_outreach_email_task(subject_line, message, receiver, user, send_to_list):
    cc_s = [email.strip() for email in send_to_list.split(",") if send_to_list] + [user.email]
    logger.info(f"Sending email to {receiver} with cc {cc_s}")
    email = EmailMessage(
        subject=subject_line,
        body=message,
        from_email="Rasul Kireev <rasul@gettalentleads.com>",
        to=[receiver],
        reply_to=[user.email],
        cc=cc_s,
    )
    email.send(fail_silently=True)
