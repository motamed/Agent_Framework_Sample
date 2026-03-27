# Build Your First AI Agent: The Automated Travel Planner

The holidays are just around the corner, and the familiar feeling of wanderlust is setting in. Where should you go? What should you do? The planning can be as daunting as it is exciting. But what if you could delegate that initial spark of inspiration to a smart assistant?

In this tutorial, we'll build exactly that: a personal AI travel agent. This agent will use the **Microsoft Agent Framework** to dream up a random vacation spot and instantly create a detailed day-trip itinerary for it. We'll use **GitHub Models** as our AI engine, providing a powerful yet accessible entry point into the world of AI agents.

We will walk through the entire process step-by-step, providing complete code examples for both **.NET (C\#)** and **Python**.

### Prerequisites: Configuring Your Environment

Before we start coding, we need to set up the configuration required to connect to the AI model. The Microsoft Agent Framework supports various AI solutions, and for this tutorial, we are focusing on **GitHub Models**.

To securely manage our credentials (like API keys), we will create a file named `.env`. This file stores sensitive information that our code will read, preventing us from hard-coding it directly.

Please create a file named `.env` in the root of your project and add the following content. You will need to replace the placeholder text in the quotes with your actual information.

```
GITHUB_TOKEN="Your GitHub Models Token"
GITHUB_ENDPOINT="Your GitHub Models Endpoint"
GITHUB_MODEL_ID="Your GitHub Model ID"
```

**Configuration Details:**

  * **`GITHUB_TOKEN`**: This is your access token for GitHub Models. It serves as your credential to use the service.
  * **`GITHUB_ENDPOINT`**: This is the API endpoint for the GitHub Models service. Our code will send requests to this URL.
  * **`GITHUB_MODEL_ID`**: This is the specific name or ID of the AI model you intend to use.

Once this configuration is in place, the .NET and Python code in the tutorial will be able to read these environment variables and successfully connect to GitHub Models to create your first AI Agent.

-----

## Part 1: Building the Travel Agent with .NET (C\#)

Let's start by building our agent in a .NET environment using a C\# notebook.

### Step 1: Setting Up the Environment

First, we need to load the necessary libraries. This includes the core Microsoft Agent Framework libraries and a helper for managing environment variables.

```csharp
// Reference the core AI extensions library from NuGet
#r "nuget: Microsoft.Extensions.AI, 9.9.0"
#r "nuget: Microsoft.Extensions.AI.OpenAI, 9.9.0-preview.1.25458.4"

// Reference local Agent Framework libraries
#r "C:\\Users\\kinfeylo\\Documents\\Agent\\agent-framework\\dotnet\\src\\Microsoft.Agents.AI.OpenAI\\bin\\Debug\\net9.0\\Microsoft.Agents.AI.OpenAI.dll"
#r "C:\\Users\\kinfeylo\\Documents\\Agent\\agent-framework\\dotnet\\src\\Microsoft.Agents.AI\\bin\\Debug\\net9.0\\Microsoft.Agents.AI.dll"

// Add a helper for loading environment variables
#r "nuget: DotNetEnv, 3.1.1"

// Import the necessary namespaces
using System;
using System.ComponentModel;
using System.ClientModel;
using Microsoft.Extensions.AI;
using Microsoft.Agents.AI;
using OpenAI;
using DotNetEnv;
```

### Step 2: Loading Configuration

Now, we'll load the `.env` file and read the values we defined earlier.

```csharp
// Load variables from a .env file located in a parent directory
Env.Load("../../../.env");

// Fetch the GitHub endpoint, model ID, and API token
var github_endpoint = Environment.GetEnvironmentVariable("GITHUB_ENDPOINT") ?? throw new InvalidOperationException("GITHUB_ENDPOINT is not set.");
var github_model_id = Environment.GetEnvironmentVariable("GITHUB_MODEL_ID") ?? "gpt-4o-mini";
var github_token = Environment.GetEnvironmentVariable("GITHUB_TOKEN") ?? throw new InvalidOperationException("GITHUB_TOKEN is not set.");
```

### Step 3: Creating a Custom Tool

Our agent needs a special skill: the ability to pick a vacation destination. We'll give it a "tool" for this. A tool is simply a function the agent can call to get information or perform an action. The `[Description]` attribute is crucial, as it tells the AI what the tool does.

```csharp
[Description("Provides a random vacation destination.")]
static string GetRandomDestination()
{
    var destinations = new List<string>
    {
        "Paris, France", "Tokyo, Japan", "New York City, USA",
        "Sydney, Australia", "Rome, Italy", "Barcelona, Spain",
        "Cape Town, South Africa", "Rio de Janeiro, Brazil",
        "Bangkok, Thailand", "Vancouver, Canada"
    };

    var random = new Random();
    int index = random.Next(destinations.Count);
    return destinations[index];
}
```

### Step 4: Building and Running the Agent

It's time to assemble our agent. We first configure the `OpenAIClient` to point to the GitHub Models endpoint. Then, we create the agent, giving it two key things:

1.  **Instructions**: A clear directive on its personality and goal.
2.  **Tools**: The `GetRandomDestination` function we just created.

Finally, we give it a prompt and let it run\!

```csharp
// Configure the client options to point to the GitHub endpoint
var openAIOptions = new OpenAIClientOptions()
{
    Endpoint = new Uri(github_endpoint)
};

// Create the client with our API token and options
var openAIClient = new OpenAIClient(new ApiKeyCredential(github_token), openAIOptions);

// Create the AIAgent
AIAgent agent = openAIClient.GetChatClient(github_model_id).CreateAIAgent(
    instructions: "You are a helpful AI Agent that can help plan vacations for customers at random destinations",
    tools: [AIFunctionFactory.Create((Func<string>)GetRandomDestination)]
);

// Run the agent and print the result
Console.WriteLine(await agent.RunAsync("Plan me a day trip"));
```

When you run this, the agent will first call the `GetRandomDestination()` tool to pick a city. It will then use its AI capabilities to generate a detailed itinerary for that city, like this one for Cape Town:

```
How about a day trip to Cape Town, South Africa? Here's a suggested itinerary for your day:

### Morning
- **Breakfast at a local café**: Start your day with a delicious breakfast at one of Cape Town's charming cafés. Try some local dishes like breakfast Bobotie or a hearty South African braai (barbecue).
- **Table Mountain**: After breakfast, take a cable car to the top of Table Mountain for breathtaking views of the city and coastline. Spend some time hiking the various trails on the mountain.

### Midday
- **Visit the V&A Waterfront**: Head down to the V&A Waterfront for lunch. You'll find plenty of dining options with beautiful harbor views. Don’t miss the local seafood!
...
```

-----

## Part 2: Building the Travel Agent with Python

Next, let's build the same agent using Python, which offers a more concise syntax for similar operations.

### Step 1: Setting Up the Environment

We begin by importing the required libraries. The `agent_framework` provides the core building blocks, while `dotenv` helps us manage our configuration securely.

```python
import os
from random import randint
from dotenv import load_dotenv

# Import the core agent components
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

# Load environment variables from the .env file
load_dotenv()
```

### Step 2: Creating a Custom Tool

Just like in .NET, we need to define a function that our agent can use as a tool. In Python, the function's docstring (`"""..."""`) serves the same purpose as the `[Description]` attribute, telling the agent what the function is for.

```python
def get_random_destination() -> str:
    """Get a random vacation destination."""
    destinations = [
        "Barcelona, Spain", "Paris, France", "Berlin, Germany",
        "Tokyo, Japan", "Sydney, Australia", "New York, USA",
        "Cairo, Egypt", "Cape Town, South Africa",
        "Rio de Janeiro, Brazil", "Bali, Indonesia"
    ]
    return destinations[randint(0, len(destinations) - 1)]
```

### Step 3: Building and Running the Agent

With our tool ready, we can initialize the `OpenAIChatClient`, pulling the configuration directly from the environment variables. Then, we create our `ChatAgent`, providing it with the same instructions and the `get_random_destination` tool.

```python
# Initialize the chat client pointing to the GitHub Models service
openai_chat_client = OpenAIChatClient(
    base_url=os.environ.get("GITHUB_ENDPOINT"), 
    api_key=os.environ.get("GITHUB_TOKEN"), 
    ai_model_id=os.environ.get("GITHUB_MODEL_ID")
)

# Create the agent
agent = ChatAgent(
        chat_client=openai_chat_client,
        instructions="You are a helpful AI Agent that can help plan vacations for customers at random destinations.",
        tools=[get_random_destination]
)

# Run the agent with a prompt
response = await agent.run("Plan me a day trip")
```

The `response` object contains the full conversation history. To display the final travel plan, we extract the text from the agent's last message.

```python
# Get the text from the last message in the response
last_message = response.messages[-1]
text_content = last_message.contents[0].text
print("Travel plan:")
print(text_content)
```

The output will be a beautifully crafted itinerary for a randomly chosen destination, such as Rio de Janeiro:

```
Travel plan:
I have selected a fantastic destination for your day trip: Rio de Janeiro, Brazil! Here’s a suggested itinerary for your adventure:

### Morning
- **Breakfast at Confeitaria Colombo**: Start your day with a delicious Brazilian breakfast at this historic café known for its stunning architecture and great pastries.
- **Visit Christ the Redeemer**: Head to the iconic Christ the Redeemer statue. Take a train ride to the top and enjoy the breathtaking views of the city.

### Afternoon
- **Lunch at a Local Churrascaria**: Enjoy a traditional Brazilian barbecue at a regionally favored churrascaria. Savor an assortment of grilled meats and side dishes.
...
```

## Conclusion

Congratulations\! You have successfully built a functional AI travel agent using the Microsoft Agent Framework in both .NET and Python. You've learned how to give an agent a specific purpose, equip it with custom tools to perform actions, and set it to work on a task. This is the foundation of building even more complex and powerful AI agents.