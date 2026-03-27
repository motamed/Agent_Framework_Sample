# Tutorial: Building an Agent with RAG Functionality

This tutorial will guide you through building a Retrieval-Augmented Generation (RAG) agent using both .NET (C\#) and Python with Azure AI. We will cover the basic concepts of RAG and then walk through code examples that demonstrate how to implement an agent that can answer questions based on a provided document.

## 1\. Understanding RAG

### What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that enhances the capabilities of Large Language Models (LLMs) by grounding them in external sources of knowledge. It combines two main components:

  * **Retriever:** This component is responsible for searching and retrieving relevant information from a knowledge base (e.g., a collection of documents).
  * **Generator:** This is a standard LLM that takes the retrieved information as context and uses it to generate a comprehensive and accurate answer to the user's query.

By providing the LLM with relevant, up-to-date information, RAG helps to reduce hallucinations (making up facts) and allows the model to answer questions about specific, private data it wasn't trained on.

### RAG Application Scenarios

RAG is highly effective in various scenarios, including:

  * **Customer Support:** Building chatbots that can answer customer questions based on product manuals, FAQs, and internal knowledge bases.
  * **Enterprise Search:** Creating intelligent search systems that allow employees to ask questions and get precise answers from a vast repository of internal documents.
  * **Content Discovery:** Assisting users in finding and understanding information within large, complex documents like research papers, legal contracts, or financial reports.

### Creating a RAG Agent with File Search

The fundamental workflow for creating a RAG agent with a file search capability involves these steps:

1.  **Upload Knowledge:** Provide the documents that the agent will use as its knowledge base.
2.  **Create a Vector Store:** The uploaded files are indexed into a specialized database called a vector store. This allows for efficient semantic searching to find the most relevant document snippets for a given query.
3.  **Define the Agent:** Create an agent and equip it with a `File Search` tool.
4.  **Link Resources:** Connect the `File Search` tool to the vector store you created.
5.  **Instruct the Agent:** Provide a clear system prompt that instructs the agent on how to behave—for example, telling it to only use the provided files to answer questions and to admit when it doesn't know the answer.
6.  **Query the Agent:** Start a conversation and ask questions. The agent will automatically use the file search tool to retrieve context before generating its response.

-----

## 2\. Code Examples

The following examples demonstrate how to build a RAG agent using the Azure AI Agent Framework in both .NET and Python. Both examples will use a file named `demo.md` as the knowledge source.

### .NET (C\#) Example

This example uses a C\# Polyglot Notebook to create and interact with the RAG agent.

**Step 1: Setup and Dependencies**

First, we need to reference the necessary NuGet packages for the Azure AI Agent Framework, Azure identity, and environment variable management.

```csharp
#r "nuget: Microsoft.Extensions.AI, 9.9.0"
#r "nuget: Azure.AI.Agents.Persistent, 1.2.0-beta.5"
#r "nuget: Azure.Identity, 1.15.0"
#r "nuget: System.Linq.Async, 6.0.3"
#r "nuget: DotNetEnv, 3.1.1"
```

**Step 2: Load Configuration and Initialize Client**

Load environment variables from a `.env` file and create the `PersistentAgentsClient` using your Azure credentials.

```csharp
using DotNetEnv;
using Azure.AI.Agents.Persistent;
using Azure.Identity;

// Load environment variables
Env.Load("../../../.env");
var azure_foundry_endpoint = Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT") ?? throw new InvalidOperationException("AZURE_FOUNDRY_PROJECT_ENDPOINT is not set.");
var azure_foundry_model_id = Environment.GetEnvironmentVariable("FOUNDRY_MODEL_DEPLOYMENT_NAME") ?? "gpt-4.1-mini";

// Initialize the client
var persistentAgentsClient = new PersistentAgentsClient(azure_foundry_endpoint, new AzureCliCredential());
```

**Step 3: Upload File and Create Vector Store**

Upload the `demo.md` file and use its ID to create a vector store. This makes the file's content searchable.

```csharp
// Path to the local file
string pdfPath = "../files/demo.md";
var pdfStream = await Task.Run(() => File.OpenRead(pdfPath));

// Upload the file
PersistentAgentFileInfo fileInfo = await persistentAgentsClient.Files.UploadFileAsync(pdfStream, PersistentAgentFilePurpose.Agents, "demo.md");

// Create the vector store
PersistentAgentsVectorStore fileStore =
            await persistentAgentsClient.VectorStores.CreateVectorStoreAsync(
                [fileInfo.Id],
                metadata: new Dictionary<string, string>() { { "agentkey", bool.TrueString } });
```

**Step 4: Create the RAG Agent**

Define a new persistent agent. Provide it with instructions, equip it with a `FileSearchToolDefinition`, and link the tool's resources to the ID of the vector store created in the previous step.

```csharp
PersistentAgent agentModel = await persistentAgentsClient.Administration.CreateAgentAsync(
            azure_foundry_model_id,
            name: "DotNetRAGAgent",
            tools: [new FileSearchToolDefinition()],
            instructions: """
                You are a helpful assistant that helps people find information in a set of files.  If you can't find the answer in the files, just say you don't know. Do not make up an answer.
                """,
            toolResources: new()
            {
                FileSearch = new()
                {
                    VectorStoreIds = { fileStore.Id },
                }
            });
```

**Step 5: Interact with the Agent**

Get the agent, start a new conversation thread, and ask a question. The agent will use the file search tool to find the answer within `demo.md`.

```csharp
AIAgent agent = await persistentAgentsClient.GetAIAgentAsync(agentModel.Id);
AgentThread thread = agent.GetNewThread();

Console.WriteLine(await agent.RunAsync("What's graphrag?", thread));
```

**Output:**

```
GraphRAG is an AI-based content interpretation and search capability that utilizes large language models (LLMs) to parse data and create a knowledge graph. It enables the connection of information across large volumes of data, allowing it to answer complex questions that span multiple documents or that require thematic understanding. Its primary use is to support critical information discovery and analysis, especially for data that is noisy, fragmented, or involves misinformation. GraphRAG is intended for use by trained domain experts who can verify and interpret its outputs, making it suitable for specialized datasets and complex inquiries【4:0†demo.md】.
```

### Python Example

This example uses a Python script to perform the same actions.

**Step 1: Setup and Dependencies**

Import the necessary libraries for the Azure AI Agent Framework and handling environment variables.

```python
import os
from azure.ai.agents.models import FilePurpose,VectorStore,FileSearchTool
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv
from agent_framework import AgentRunResponse,ChatAgent,HostedFileSearchTool,HostedVectorStoreContent
from agent_framework.azure import AzureAIAgentClient

load_dotenv()
```

**Step 2: Define a Helper for Vector Store Creation**

This async function encapsulates the logic for uploading a file and creating a vector store from it.

```python
async def create_vector_store(client: AzureAIAgentClient) -> tuple[str, VectorStore]:
    """Create a vector store with sample documents."""
    file_path = '../files/demo.md'
    file = await client.project_client.agents.files.upload_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {file.id}")

    vector_store = await client.project_client.agents.vector_stores.create_and_poll(file_ids=[file.id], name="graph_knowledge_base")
    print(f"Created vector store, ID: {vector_store.id}")

    return file.id, vector_store
```

**Step 3: Create and Run the Agent**

The main execution block initializes the client, creates the vector store, defines the agent with the `FileSearchTool`, and runs a query. Note how the tool definitions and resources are passed during agent creation.

```python
async with (
        AzureCliCredential() as credential,
        AzureAIAgentClient(async_credential=credential) as chat_client,
    ):
        file_id, vector_store = await create_vector_store(chat_client)

        file_search = FileSearchTool(vector_store_ids=[vector_store.id])
        
        agent = chat_client.create_agent(
            name="PythonRAGDemo",
            instructions="""
                You are a helpful assistant that helps people find information in a set of files.  If you can't find the answer in the files, just say you don't know. Do not make up an answer.
                """,
            tools=file_search.definitions,  # Tools available to the agent
            tool_resources=file_search.resources,  # Resources for the tool
        )
                
        print("Agent created. You can now ask questions about the uploaded document.")

        query = "What is GraphRAG?"
        # The tool resources must be passed again at runtime
        response = await AgentRunResponse.from_agent_response_generator(agent.run_stream(query, tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}))
        print(f"Assistant: {response}")
```

**Output:**

```
Uploaded file, file ID: assistant-CiUQ5xjyFBC7TJyJ331FCF
Created vector store, ID: vs_BEbCqzLGHRRQsP0mMALlV5CV
Agent created. You can now ask questions about the uploaded document.
Assistant: GraphRAG is an AI-based content interpretation and search system that uses large language models to create a knowledge graph from a user-provided dataset. It connects information across large volumes of data to answer complex, thematic, or multi-document questions that are difficult to address through traditional keyword or vector search methods. The system is designed to support critical analysis and discovery, especially in contexts where information is noisy or spread across many sources. It emphasizes transparency, grounded responses, and resilience to injection attacks, although it relies on well-constructed indexing and human oversight for optimal performance【4:0†demo.md】.
```