import os
import json
from openai import OpenAI

# Initialize the OpenAI client with an API key from environment variables
client = OpenAI(
    api_key=os.getenv("OPENAI_KEY"),  # Retrieves the API key from the "OPENAI_KEY" environment variable
)

# Initial message from the assistant in the chat history
messages = [{"role": "assistant", "content": "How can I help?"}]

def display_chat_history(messages):
    """
    Prints the chat history to the console. Each message is displayed with the sender's role and content.

    Args:
        messages (list of dict): A list of dictionaries where each dictionary represents a message in the chat history.
                                 Each message has a 'role' key indicating who sent the message and a 'content' key with the message text.
    """
    for message in messages:
        print(f"{message['role'].capitalize()}: {message['content']}")

def get_assistant_response(messages):
    """
    Sends the current chat history to the OpenAI API to generate a response from the assistant using GPT-4o-mini.

    Args:
        messages (list of dict): The current chat history as a list of message dictionaries.

    Returns:
        str: The assistant's response as a string.

    Raises:
        Exception: Prints an error message if the API call fails and returns a default error response.
    """
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",  # The model version to use for generating responses
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            temperature=1,  # Adjust the temperature if needed
            max_tokens=1080,  # Adjust as needed
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        response = r.choices[0].message.content
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Sorry, I can't process your request right now."

def get_response(prompt: str):
    """
    Processes a user's prompt to generate and display the assistant's response using GPT-4o-mini.

    Args:
        prompt (str): The user's message to which the assistant should respond.

    Returns:
        str: The assistant's response, which is also added to the chat history and displayed along with the rest of the conversation.
    """
    # Add the user's message to the chat history
    messages.append({"role": "user", "content": prompt})

    # Get the assistant's response and add it to the chat history
    response = get_assistant_response(messages)
    messages.append({"role": "assistant", "content": response})

    # Display the updated chat history
    display_chat_history(messages)

    return response


import json

def chat_response(prompt: str, context: str = "", chat_history: list = []):
    """
    Processes a user's prompt to generate the assistant's response using GPT-4o-mini,
    with context about the environmental incident.

    Args:
        prompt (str): The user's message to which the assistant should respond.
        context (str): A JSON string containing context about the incident.
        chat_history (list): The existing chat history for this session.

    Returns:
        str: The assistant's response.

    Examples:
        >>> context = '{"type_incident": "Déforestation", "analysis": "La déforestation affecte la biodiversité locale.", "piste_solution": "Reforestation et éducation communautaire."}'
        >>> prompt = "Quels sont les impacts de la déforestation dans cette zone ?"
        >>> chat_response(prompt, context)
        'La déforestation affecte la biodiversité locale en réduisant les habitats naturels des espèces. Pour remédier à cela, la reforestation et l'éducation communautaire sont des pistes de solution envisageables.'

        >>> context = '{"type_incident": "Pollution de l'eau", "analysis": "Les rejets industriels ont contaminé la rivière.", "piste_solution": "Installation de stations de traitement des eaux."}'
        >>> prompt = "Comment pouvons-nous améliorer la qualité de l'eau ?"
        >>> chat_response(prompt, context)
        'Les rejets industriels ont contaminé la rivière. Pour améliorer la qualité de l'eau, l'installation de stations de traitement des eaux est recommandée.'
    """

    # Parse the context JSON string to extract details about the incident
    context_obj = json.loads(context)
    incident_type = context_obj.get('type_incident', 'Inconnu')
    analysis = context_obj.get('analysis', 'Non spécifié')
    piste_solution = context_obj.get('piste_solution', 'Non spécifié')

    # Create a system message to guide the assistant's behavior with clear instructions and context
    system_message = f"""
    <system>
        <role>assistant AI</role>
        <task>analyse des incidents environnementaux</task>
        <location>Mali</location>
        <incident>
            <type>{incident_type}</type>
            <analysis>{analysis}</analysis>
            <solution_tracks>{piste_solution}</solution_tracks>
        </incident>
        <instructions>
            <instruction>Adaptez vos réponses au contexte spécifique de l'incident.</instruction>
            <instruction>Utilisez les informations de contexte pour enrichir vos explications.</instruction>
            <instruction>Si la question dépasse le contexte fourni, mentionnez clairement que vous répondez de manière générale.</instruction>
            <instruction>Priorisez les réponses concises et orientées sur la résolution du problème.</instruction>
            <instruction>Ne déviez pas de la tâche principale et évitez les réponses non pertinentes.</instruction>
            <response_formatting>
                <formatting_rule>Répondez de manière concise, avec une longueur de réponse idéale de 2 à 3 phrases.</formatting_rule>
                <formatting_rule>Fournissez une réponse structurée : commencez par le problème principal, suivez avec la solution proposée.</formatting_rule>
                <formatting_rule>Utilisez des mots simples et clairs, évitez le jargon technique inutile.</formatting_rule>
                <formatting_rule>Donnez des informations essentielles en utilisant un langage direct et précis.</formatting_rule>
                <formatting_rule>Si une recommandation est faite, assurez-vous qu'elle est faisable et contextualisée.</formatting_rule>
            </response_formatting>
        </instructions>
        <examples>
            <example>
                <prompt>Quels sont les impacts de la déforestation dans cette zone ?</prompt>
                <response>La déforestation affecte la biodiversité locale en réduisant les habitats naturels des espèces. Pour remédier à cela, la reforestation et l'éducation communautaire sont des pistes de solution envisageables.</response>
            </example>
            <example>
                <prompt>Comment pouvons-nous améliorer la qualité de l'eau ?</prompt>
                <response>Les rejets industriels ont contaminé la rivière. Pour améliorer la qualité de l'eau, l'installation de stations de traitement des eaux est recommandée.</response>
            </example>
            <example>
                <prompt>Que peut-on faire pour limiter l'érosion des sols dans cette région ?</prompt>
                <response>L'érosion des sols est exacerbée par la déforestation et les pratiques agricoles non durables. Pour limiter l'érosion, il est recommandé de pratiquer l'agroforesterie, de planter des haies pour protéger les sols, et de promouvoir des techniques agricoles conservatrices.</response>
            </example>
            <example>
                <prompt>Quelles sont les conséquences de la pollution de l'air sur la santé publique ici ?</prompt>
                <response>La pollution de l'air, principalement due aux émissions industrielles et à la combustion de biomasse, a des effets négatifs sur la santé publique, notamment des problèmes respiratoires et cardiovasculaires. Pour atténuer ces impacts, il est essentiel de réduire les sources d'émissions et de promouvoir des énergies plus propres.</response>
            </example>
            <example>
                <prompt>Comment réduire l'impact de la pollution plastique sur l'environnement local ?</prompt>
                <response>La pollution plastique peut être réduite en mettant en place des systèmes de collecte et de recyclage des déchets, en sensibilisant la population à la réduction de l'utilisation du plastique, et en favorisant des alternatives biodégradables.</response>
            </example>
            <example>
                <prompt>Quelles mesures peuvent être prises pour protéger la faune menacée dans cette région ?</prompt>
                <response>Pour protéger la faune menacée, il est crucial de créer des zones protégées, de lutter contre le braconnage, et de promouvoir des pratiques agricoles respectueuses de l'environnement qui minimisent la destruction des habitats naturels.</response>
            </example>
            <example>
                <prompt>Parlons de musique !</prompt>
                <response>Je comprends que vous souhaitez parler de musique. Toutefois, ma tâche principale est d'analyser les incidents environnementaux. Si vous avez des questions sur un incident environnemental, je serais ravi de vous aider.</response>
            </example>
            <example>
                <prompt>Avez-vous vu le dernier film populaire ?</prompt>
                <response>Je ne suis pas programmé pour discuter des films récents. Mon rôle est de vous assister dans l'analyse des incidents environnementaux. Revenons à ce sujet, si vous le voulez bien.</response>
            </example>
            <example>
                <prompt>Quels sont les meilleurs restaurants ici ?</prompt>
                <response>Je me concentre actuellement sur l'analyse des incidents environnementaux. Pour toute question relative aux incidents ou à des pistes de solution, je suis prêt à vous aider.</response>
            </example>
        </examples>
    </system>
    """

    # Build the list of messages for the conversation with roles defined for each message
    messages = [
        {"role": "system", "content": system_message},
    ] + chat_history + [{"role": "user", "content": prompt}]

    try:
        # Get the assistant's response
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Ensure the model is available and correctly specified
            messages=messages,
            temperature=0.5,  # Reduce temperature for more focused and grounded responses
            max_tokens=1080,
            top_p=0.8,  # Encourage more reliable answers by modifying top_p
            frequency_penalty=0.3,  # Penalize repetition for more diverse outputs
            presence_penalty=0.0  # Remove presence penalty to avoid deviation from the task
        )

        assistant_response = response.choices[0].message.content
        return assistant_response

    except Exception as e:
        print(f"An error occurred: {e}")
        return "Désolé, je ne peux pas traiter votre demande pour le moment."

