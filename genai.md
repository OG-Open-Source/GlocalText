# migrate.md

Starting with the Gemini 2.0 release in late 2024, we introduced a new set of
libraries called the [Google GenAI SDK](https://ai.google.dev/gemini-api/docs/libraries). It offers
an improved developer experience through
an [updated client architecture](https://ai.google.dev/gemini-api/docs/migrate#client), and
[simplifies the transition](https://ai.google.dev/gemini-api/docs/migrate-to-cloud) between developer
and enterprise workflows.

The Google GenAI SDK is now in [General Availability (GA)](https://ai.google.dev/gemini-api/docs/libraries#new-libraries) across all supported
platforms. If you're using one of our [legacy libraries](https://ai.google.dev/gemini-api/docs/libraries#previous-sdks), we strongly recommend you to
migrate.

This guide provides before-and-after examples of migrated code to help you get
started.
| **Note:** The Go examples omit imports and other boilerplate code to improve readability.

## Installation

**Before**

### Python

    pip install -U -q "google-generativeai"

### JavaScript

    npm install @google/generative-ai

### Go

    go get github.com/google/generative-ai-go

**After**

### Python

    pip install -U -q "google-genai"

### JavaScript

    npm install @google/genai

### Go

    go get google.golang.org/genai

## API access

The old SDK implicitly handled the API client behind the scenes using a variety
of ad hoc methods. This made it hard to manage the client and credentials.
Now, you interact through a central `Client` object. This `Client` object acts
as a single entry point for various API services (e.g., `models`, `chats`,
`files`, `tunings`), promoting consistency and simplifying credential and
configuration management across different API calls.

**Before (Less Centralized API Access)**

### Python

The old SDK didn't explicitly use a top-level client object for most API
calls. You would directly instantiate and interact with `GenerativeModel`
objects.

    import google.generativeai as genai

    # Directly create and use model objects
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(...)
    chat = model.start_chat(...)

### JavaScript

While `GoogleGenerativeAI` was a central point for models and chat, other
functionalities like file and cache management often required importing and
instantiating entirely separate client classes.

    import { GoogleGenerativeAI } from "@google/generative-ai";
    import { GoogleAIFileManager, GoogleAICacheManager } from "@google/generative-ai/server"; // For files/caching

    const genAI = new GoogleGenerativeAI("YOUR_API_KEY");
    const fileManager = new GoogleAIFileManager("YOUR_API_KEY");
    const cacheManager = new GoogleAICacheManager("YOUR_API_KEY");

    // Get a model instance, then call methods on it
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
    const result = await model.generateContent(...);
    const chat = model.startChat(...);

    // Call methods on separate client objects for other services
    const uploadedFile = await fileManager.uploadFile(...);
    const cache = await cacheManager.create(...);

### Go

The `genai.NewClient` function created a client, but generative model
operations were typically called on a separate `GenerativeModel` instance
obtained from this client. Other services might have been accessed via
distinct packages or patterns.

    import (
          "github.com/google/generative-ai-go/genai"
          "github.com/google/generative-ai-go/genai/fileman" // For files
          "google.golang.org/api/option"
    )

    client, err := genai.NewClient(ctx, option.WithAPIKey("YOUR_API_KEY"))
    fileClient, err := fileman.NewClient(ctx, option.WithAPIKey("YOUR_API_KEY"))

    // Get a model instance, then call methods on it
    model := client.GenerativeModel("gemini-1.5-flash")
    resp, err := model.GenerateContent(...)
    cs := model.StartChat()

    // Call methods on separate client objects for other services
    uploadedFile, err := fileClient.UploadFile(...)

**After (Centralized Client Object)**

### Python

    from google import genai

    # Create a single client object
    client = genai.Client()

    # Access API methods through services on the client object
    response = client.models.generate_content(...)
    chat = client.chats.create(...)
    my_file = client.files.upload(...)
    tuning_job = client.tunings.tune(...)

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    // Create a single client object
    const ai = new GoogleGenAI({apiKey: "YOUR_API_KEY"});

    // Access API methods through services on the client object
    const response = await ai.models.generateContent(...);
    const chat = ai.chats.create(...);
    const uploadedFile = await ai.files.upload(...);
    const cache = await ai.caches.create(...);

### Go

    import "google.golang.org/genai"

    // Create a single client object
    client, err := genai.NewClient(ctx, nil)

    // Access API methods through services on the client object
    result, err := client.Models.GenerateContent(...)
    chat, err := client.Chats.Create(...)
    uploadedFile, err := client.Files.Upload(...)
    tuningJob, err := client.Tunings.Tune(...)

## Authentication

Both legacy and new libraries authenticate using API keys. You can
[create](https://aistudio.google.com/app/apikey) your API key in Google AI
Studio.

**Before**

### Python

The old SDK handled the API client object implicitly.

    import google.generativeai as genai

    genai.configure(api_key=...)

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");

### Go

Import the Google libraries:

    import (
          "github.com/google/generative-ai-go/genai"
          "google.golang.org/api/option"
    )

Create the client:

    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))

**After**

### Python

With Google GenAI SDK, you create an API client first, which is used to call
the API.
The new SDK will pick up your API key from either one of the
`GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variables, if you don't
pass one to the client.

    export GEMINI_API_KEY="YOUR_API_KEY"

    from google import genai

    client = genai.Client() # Set the API key using the GEMINI_API_KEY env var.
                            # Alternatively, you could set the API key explicitly:
                            # client = genai.Client(api_key="your_api_key")

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({apiKey: "GEMINI_API_KEY"});

### Go

Import the GenAI library:

    import "google.golang.org/genai"

Create the client:

    client, err := genai.NewClient(ctx, &genai.ClientConfig{
            Backend:  genai.BackendGeminiAPI,
    })

## Generate content

### Text

**Before**

### Python

Previously, there were no client objects, you accessed APIs directly through
`GenerativeModel` objects.

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        'Tell me a story in 300 words'
    )
    print(response.text)

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI(process.env.API_KEY);
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
    const prompt = "Tell me a story in 300 words";

    const result = await model.generateContent(prompt);
    console.log(result.response.text());

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    model := client.GenerativeModel("gemini-1.5-flash")
    resp, err := model.GenerateContent(ctx, genai.Text("Tell me a story in 300 words."))
    if err != nil {
        log.Fatal(err)
    }

    printResponse(resp) // utility for printing response parts

**After**

### Python

The new Google GenAI SDK provides access to all the API methods through the
`Client` object. Except for a few stateful special cases (`chat` and
live-api `session`s), these are all stateless functions. For utility and
uniformity, objects returned are `pydantic` classes.

    from google import genai
    client = genai.Client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Tell me a story in 300 words.'
    )
    print(response.text)

    print(response.model_dump_json(
        exclude_none=True, indent=4))

### JavaScript

    import { GoogleGenAI } from "@google/genai";

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });

    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: "Tell me a story in 300 words.",
    });
    console.log(response.text);

### Go

    ctx := context.Background()
      client, err := genai.NewClient(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }

    result, err := client.Models.GenerateContent(ctx, "gemini-2.0-flash", genai.Text("Tell me a story in 300 words."), nil)
    if err != nil {
        log.Fatal(err)
    }
    debugPrint(result) // utility for printing result

### Image

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([
        'Tell me a story based on this image',
        Image.open(image_path)
    ])
    print(response.text)

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    function fileToGenerativePart(path, mimeType) {
      return {
        inlineData: {
          data: Buffer.from(fs.readFileSync(path)).toString("base64"),
          mimeType,
        },
      };
    }

    const prompt = "Tell me a story based on this image";

    const imagePart = fileToGenerativePart(
      `path/to/organ.jpg`,
      "image/jpeg",
    );

    const result = await model.generateContent([prompt, imagePart]);
    console.log(result.response.text());

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    model := client.GenerativeModel("gemini-1.5-flash")

    imgData, err := os.ReadFile("path/to/organ.jpg")
    if err != nil {
        log.Fatal(err)
    }

    resp, err := model.GenerateContent(ctx,
        genai.Text("Tell me about this instrument"),
        genai.ImageData("jpeg", imgData))
    if err != nil {
        log.Fatal(err)
    }

    printResponse(resp) // utility for printing response

**After**

### Python

Many of the same convenience features exist in the new SDK. For
example, `PIL.Image` objects are automatically converted.

    from google import genai
    from PIL import Image

    client = genai.Client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            'Tell me a story based on this image',
            Image.open(image_path)
        ]
    )
    print(response.text)

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });

    const organ = await ai.files.upload({
      file: "path/to/organ.jpg",
    });

    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: [
        createUserContent([
          "Tell me a story based on this image",
          createPartFromUri(organ.uri, organ.mimeType)
        ]),
      ],
    });
    console.log(response.text);

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }

    imgData, err := os.ReadFile("path/to/organ.jpg")
    if err != nil {
        log.Fatal(err)
    }

    parts := []*genai.Part{
        {Text: "Tell me a story based on this image"},
        {InlineData: &genai.Blob{Data: imgData, MIMEType: "image/jpeg"}},
    }
    contents := []*genai.Content{
        {Parts: parts},
    }

    result, err := client.Models.GenerateContent(ctx, "gemini-2.0-flash", contents, nil)
    if err != nil {
        log.Fatal(err)
    }
    debugPrint(result) // utility for printing result

### Streaming

**Before**

### Python

    import google.generativeai as genai

    response = model.generate_content(
        "Write a cute story about cats.",
        stream=True)
    for chunk in response:
        print(chunk.text)

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    const prompt = "Write a story about a magic backpack.";

    const result = await model.generateContentStream(prompt);

    // Print text as it comes in.
    for await (const chunk of result.stream) {
      const chunkText = chunk.text();
      process.stdout.write(chunkText);
    }

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    model := client.GenerativeModel("gemini-1.5-flash")
    iter := model.GenerateContentStream(ctx, genai.Text("Write a story about a magic backpack."))
    for {
        resp, err := iter.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            log.Fatal(err)
        }
        printResponse(resp) // utility for printing the response
    }

**After**

### Python

    from google import genai

    client = genai.Client()

    for chunk in client.models.generate_content_stream(
      model='gemini-2.0-flash',
      contents='Tell me a story in 300 words.'
    ):
        print(chunk.text)

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });

    const response = await ai.models.generateContentStream({
      model: "gemini-2.0-flash",
      contents: "Write a story about a magic backpack.",
    });
    let text = "";
    for await (const chunk of response) {
      console.log(chunk.text);
      text += chunk.text;
    }

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }

    for result, err := range client.Models.GenerateContentStream(
        ctx,
        "gemini-2.0-flash",
        genai.Text("Write a story about a magic backpack."),
        nil,
    ) {
        if err != nil {
            log.Fatal(err)
        }
        fmt.Print(result.Candidates[0].Content.Parts[0].Text)
    }

## Configuration

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel(
      'gemini-1.5-flash',
        system_instruction='you are a story teller for kids under 5 years old',
        generation_config=genai.GenerationConfig(
          max_output_tokens=400,
          top_k=2,
          top_p=0.5,
          temperature=0.5,
          response_mime_type='application/json',
          stop_sequences=['\n'],
        )
    )
    response = model.generate_content('tell me a story in 100 words')

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      generationConfig: {
        candidateCount: 1,
        stopSequences: ["x"],
        maxOutputTokens: 20,
        temperature: 1.0,
      },
    });

    const result = await model.generateContent(
      "Tell me a story about a magic backpack.",
    );
    console.log(result.response.text())

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    model := client.GenerativeModel("gemini-1.5-flash")
    model.SetTemperature(0.5)
    model.SetTopP(0.5)
    model.SetTopK(2.0)
    model.SetMaxOutputTokens(100)
    model.ResponseMIMEType = "application/json"
    resp, err := model.GenerateContent(ctx, genai.Text("Tell me about New York"))
    if err != nil {
        log.Fatal(err)
    }
    printResponse(resp) // utility for printing response

**After**

### Python

For all methods in the new SDK, the required arguments are provided as
keyword arguments. All optional inputs are provided in the `config`
argument. Config arguments can be specified as either Python dictionaries or
`Config` classes in the `google.genai.types` namespace. For utility and
uniformity, all definitions within the `types` module are `pydantic`
classes.

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
      model='gemini-2.0-flash',
      contents='Tell me a story in 100 words.',
      config=types.GenerateContentConfig(
          system_instruction='you are a story teller for kids under 5 years old',
          max_output_tokens= 400,
          top_k= 2,
          top_p= 0.5,
          temperature= 0.5,
          response_mime_type= 'application/json',
          stop_sequences= ['\n'],
          seed=42,
      ),
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });

    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: "Tell me a story about a magic backpack.",
      config: {
        candidateCount: 1,
        stopSequences: ["x"],
        maxOutputTokens: 20,
        temperature: 1.0,
      },
    });

    console.log(response.text);

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }

    result, err := client.Models.GenerateContent(ctx,
        "gemini-2.0-flash",
        genai.Text("Tell me about New York"),
        &genai.GenerateContentConfig{
            Temperature:      genai.Ptr[float32](0.5),
            TopP:             genai.Ptr[float32](0.5),
            TopK:             genai.Ptr[float32](2.0),
            ResponseMIMEType: "application/json",
            StopSequences:    []string{"Yankees"},
            CandidateCount:   2,
            Seed:             genai.Ptr[int32](42),
            MaxOutputTokens:  128,
            PresencePenalty:  genai.Ptr[float32](0.5),
            FrequencyPenalty: genai.Ptr[float32](0.5),
        },
    )
    if err != nil {
        log.Fatal(err)
    }
    debugPrint(result) // utility for printing response

## Safety settings

Generate a response with safety settings:

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        'say something bad',
        safety_settings={
            'HATE': 'BLOCK_ONLY_HIGH',
            'HARASSMENT': 'BLOCK_ONLY_HIGH',
      }
    )

### JavaScript

    import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      safetySettings: [
        {
          category: HarmCategory.HARM_CATEGORY_HARASSMENT,
          threshold: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
      ],
    });

    const unsafePrompt =
      "I support Martians Soccer Club and I think " +
      "Jupiterians Football Club sucks! Write an ironic phrase telling " +
      "them how I feel about them.";

    const result = await model.generateContent(unsafePrompt);

    try {
      result.response.text();
    } catch (e) {
      console.error(e);
      console.log(result.response.candidates[0].safetyRatings);
    }

**After**

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
      model='gemini-2.0-flash',
      contents='say something bad',
      config=types.GenerateContentConfig(
          safety_settings= [
              types.SafetySetting(
                  category='HARM_CATEGORY_HATE_SPEECH',
                  threshold='BLOCK_ONLY_HIGH'
              ),
          ]
      ),
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const unsafePrompt =
      "I support Martians Soccer Club and I think " +
      "Jupiterians Football Club sucks! Write an ironic phrase telling " +
      "them how I feel about them.";

    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: unsafePrompt,
      config: {
        safetySettings: [
          {
            category: "HARM_CATEGORY_HARASSMENT",
            threshold: "BLOCK_ONLY_HIGH",
          },
        ],
      },
    });

    console.log("Finish reason:", response.candidates[0].finishReason);
    console.log("Safety ratings:", response.candidates[0].safetyRatings);

## Async

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content_async(
        'tell me a story in 100 words'
    )

**After**

### Python

To use the new SDK with `asyncio`, there is a separate `async`
implementation of every method under `client.aio`.

    from google import genai

    client = genai.Client()

    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash',
        contents='Tell me a story in 300 words.'
    )

## Chat

Start a chat and send a message to the model:

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    chat = model.start_chat()

    response = chat.send_message(
        "Tell me a story in 100 words")
    response = chat.send_message(
        "What happened after that?")

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
    const chat = model.startChat({
      history: [
        {
          role: "user",
          parts: [{ text: "Hello" }],
        },
        {
          role: "model",
          parts: [{ text: "Great to meet you. What would you like to know?" }],
        },
      ],
    });
    let result = await chat.sendMessage("I have 2 dogs in my house.");
    console.log(result.response.text());
    result = await chat.sendMessage("How many paws are in my house?");
    console.log(result.response.text());

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, option.WithAPIKey("GOOGLE_API_KEY"))
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    model := client.GenerativeModel("gemini-1.5-flash")
    cs := model.StartChat()

    cs.History = []*genai.Content{
        {
            Parts: []genai.Part{
                genai.Text("Hello, I have 2 dogs in my house."),
            },
            Role: "user",
        },
        {
            Parts: []genai.Part{
                genai.Text("Great to meet you. What would you like to know?"),
            },
            Role: "model",
        },
    }

    res, err := cs.SendMessage(ctx, genai.Text("How many paws are in my house?"))
    if err != nil {
        log.Fatal(err)
    }
    printResponse(res) // utility for printing the response

**After**

### Python

    from google import genai

    client = genai.Client()

    chat = client.chats.create(model='gemini-2.0-flash')

    response = chat.send_message(
        message='Tell me a story in 100 words')
    response = chat.send_message(
        message='What happened after that?')

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const chat = ai.chats.create({
      model: "gemini-2.0-flash",
      history: [
        {
          role: "user",
          parts: [{ text: "Hello" }],
        },
        {
          role: "model",
          parts: [{ text: "Great to meet you. What would you like to know?" }],
        },
      ],
    });

    const response1 = await chat.sendMessage({
      message: "I have 2 dogs in my house.",
    });
    console.log("Chat response 1:", response1.text);

    const response2 = await chat.sendMessage({
      message: "How many paws are in my house?",
    });
    console.log("Chat response 2:", response2.text);

### Go

    ctx := context.Background()
    client, err := genai.NewClient(ctx, nil)
    if err != nil {
        log.Fatal(err)
    }

    chat, err := client.Chats.Create(ctx, "gemini-2.0-flash", nil, nil)
    if err != nil {
        log.Fatal(err)
    }

    result, err := chat.SendMessage(ctx, genai.Part{Text: "Hello, I have 2 dogs in my house."})
    if err != nil {
        log.Fatal(err)
    }
    debugPrint(result) // utility for printing result

    result, err = chat.SendMessage(ctx, genai.Part{Text: "How many paws are in my house?"})
    if err != nil {
        log.Fatal(err)
    }
    debugPrint(result) // utility for printing result

## Function calling

**Before**

### Python

    import google.generativeai as genai
    from enum import Enum

    def get_current_weather(location: str) -> str:
        """Get the current whether in a given location.

        Args:
            location: required, The city and state, e.g. San Franciso, CA
            unit: celsius or fahrenheit
        """
        print(f'Called with: {location=}')
        return "23C"

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[get_current_weather]
    )

    response = model.generate_content("What is the weather in San Francisco?")
    function_call = response.candidates[0].parts[0].function_call

**After**

### Python

In the new SDK, automatic function calling is the default. Here, you disable
it.

    from google import genai
    from google.genai import types

    client = genai.Client()

    def get_current_weather(location: str) -> str:
        """Get the current whether in a given location.

        Args:
            location: required, The city and state, e.g. San Franciso, CA
            unit: celsius or fahrenheit
        """
        print(f'Called with: {location=}')
        return "23C"

    response = client.models.generate_content(
      model='gemini-2.0-flash',
      contents="What is the weather like in Boston?",
      config=types.GenerateContentConfig(
          tools=[get_current_weather],
          automatic_function_calling={'disable': True},
      ),
    )

    function_call = response.candidates[0].content.parts[0].function_call

### Automatic function calling

**Before**

### Python

The old SDK only supports automatic function calling in chat. In the new SDK
this is the default behavior in `generate_content`.

    import google.generativeai as genai

    def get_current_weather(city: str) -> str:
        return "23C"

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools=[get_current_weather]
    )

    chat = model.start_chat(
        enable_automatic_function_calling=True)
    result = chat.send_message("What is the weather in San Francisco?")

**After**

### Python

    from google import genai
    from google.genai import types
    client = genai.Client()

    def get_current_weather(city: str) -> str:
        return "23C"

    response = client.models.generate_content(
      model='gemini-2.0-flash',
      contents="What is the weather like in Boston?",
      config=types.GenerateContentConfig(
          tools=[get_current_weather]
      ),
    )

## Code execution

Code execution is a tool that allows the model to generate Python code, run it,
and return the result.

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools="code_execution"
    )

    result = model.generate_content(
      "What is the sum of the first 50 prime numbers? Generate and run code for "
      "the calculation, and make sure you get all 50.")

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      tools: [{ codeExecution: {} }],
    });

    const result = await model.generateContent(
      "What is the sum of the first 50 prime numbers? " +
        "Generate and run code for the calculation, and make sure you get " +
        "all 50.",
    );

    console.log(result.response.text());

**After**

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='What is the sum of the first 50 prime numbers? Generate and run '
                'code for the calculation, and make sure you get all 50.',
        config=types.GenerateContentConfig(
            tools=[types.Tool(code_execution=types.ToolCodeExecution)],
        ),
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });

    const response = await ai.models.generateContent({
      model: "gemini-2.0-pro-exp-02-05",
      contents: `Write and execute code that calculates the sum of the first 50 prime numbers.
                Ensure that only the executable code and its resulting output are generated.`,
    });

    // Each part may contain text, executable code, or an execution result.
    for (const part of response.candidates[0].content.parts) {
      console.log(part);
      console.log("\n");
    }

    console.log("-".repeat(80));
    // The `.text` accessor concatenates the parts into a markdown-formatted text.
    console.log("\n", response.text);

## Search grounding

`GoogleSearch` (Gemini\>=2.0) and `GoogleSearchRetrieval` (Gemini \< 2.0) are
tools that allow the model to retrieve public web data for grounding, powered by
Google.

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        contents="what is the Google stock price?",
        tools='google_search_retrieval'
    )

**After**

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='What is the Google stock price?',
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )
    )

## JSON response

Generate answers in JSON format.

**Before**

### Python

By specifying a `response_schema` and setting
`response_mime_type="application/json"` users can constrain the model to
produce a `JSON` response following a given structure.

    import google.generativeai as genai
    import typing_extensions as typing

    class CountryInfo(typing.TypedDict):
        name: str
        population: int
        capital: str
        continent: str
        major_cities: list[str]
        gdp: int
        official_language: str
        total_area_sq_mi: int

    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    result = model.generate_content(
        "Give me information of the United States",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema = CountryInfo
        ),
    )

### JavaScript

    import { GoogleGenerativeAI, SchemaType } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");

    const schema = {
      description: "List of recipes",
      type: SchemaType.ARRAY,
      items: {
        type: SchemaType.OBJECT,
        properties: {
          recipeName: {
            type: SchemaType.STRING,
            description: "Name of the recipe",
            nullable: false,
          },
        },
        required: ["recipeName"],
      },
    };

    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-pro",
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: schema,
      },
    });

    const result = await model.generateContent(
      "List a few popular cookie recipes.",
    );
    console.log(result.response.text());

**After**

### Python

The new SDK uses
`pydantic` classes to provide the schema (although you can pass a
`genai.types.Schema`, or equivalent `dict`). When possible, the SDK will
parse the returned JSON, and return the result in `response.parsed`. If you
provided a `pydantic` class as the schema the SDK will convert that `JSON`
to an instance of the class.

    from google import genai
    from pydantic import BaseModel

    client = genai.Client()

    class CountryInfo(BaseModel):
        name: str
        population: int
        capital: str
        continent: str
        major_cities: list[str]
        gdp: int
        official_language: str
        total_area_sq_mi: int

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Give me information of the United States.',
        config={
            'response_mime_type': 'application/json',
            'response_schema': CountryInfo,
        },
    )

    response.parsed

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const response = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: "List a few popular cookie recipes.",
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: "array",
          items: {
            type: "object",
            properties: {
              recipeName: { type: "string" },
              ingredients: { type: "array", items: { type: "string" } },
            },
            required: ["recipeName", "ingredients"],
          },
        },
      },
    });
    console.log(response.text);

## Files

### Upload

Upload a file:

**Before**

### Python

    import requests
    import pathlib
    import google.generativeai as genai

    # Download file
    response = requests.get(
        'https://storage.googleapis.com/generativeai-downloads/data/a11.txt')
    pathlib.Path('a11.txt').write_text(response.text)

    file = genai.upload_file(path='a11.txt')

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([
        'Can you summarize this file:',
        my_file
    ])
    print(response.text)

**After**

### Python

    import requests
    import pathlib
    from google import genai

    client = genai.Client()

    # Download file
    response = requests.get(
        'https://storage.googleapis.com/generativeai-downloads/data/a11.txt')
    pathlib.Path('a11.txt').write_text(response.text)

    my_file = client.files.upload(file='a11.txt')

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            'Can you summarize this file:',
            my_file
        ]
    )
    print(response.text)

### List and get

List uploaded files and get an uploaded file with a filename:

**Before**

### Python

    import google.generativeai as genai

    for file in genai.list_files():
      print(file.name)

    file = genai.get_file(name=file.name)

**After**

### Python

    from google import genai
    client = genai.Client()

    for file in client.files.list():
        print(file.name)

    file = client.files.get(name=file.name)

### Delete

Delete a file:

**Before**

### Python

    import pathlib
    import google.generativeai as genai

    pathlib.Path('dummy.txt').write_text(dummy)
    dummy_file = genai.upload_file(path='dummy.txt')

    file = genai.delete_file(name=dummy_file.name)

**After**

### Python

    import pathlib
    from google import genai

    client = genai.Client()

    pathlib.Path('dummy.txt').write_text(dummy)
    dummy_file = client.files.upload(file='dummy.txt')

    response = client.files.delete(name=dummy_file.name)

## Context caching

Context caching allows the user to pass the content to the model once, cache the
input tokens, and then refer to the cached tokens in subsequent calls to lower
the cost.

**Before**

### Python

    import requests
    import pathlib
    import google.generativeai as genai
    from google.generativeai import caching

    # Download file
    response = requests.get(
        'https://storage.googleapis.com/generativeai-downloads/data/a11.txt')
    pathlib.Path('a11.txt').write_text(response.text)

    # Upload file
    document = genai.upload_file(path="a11.txt")

    # Create cache
    apollo_cache = caching.CachedContent.create(
        model="gemini-1.5-flash-001",
        system_instruction="You are an expert at analyzing transcripts.",
        contents=[document],
    )

    # Generate response
    apollo_model = genai.GenerativeModel.from_cached_content(
        cached_content=apollo_cache
    )
    response = apollo_model.generate_content("Find a lighthearted moment from this transcript")

### JavaScript

    import { GoogleAICacheManager, GoogleAIFileManager } from "@google/generative-ai/server";
    import { GoogleGenerativeAI } from "@google/generative-ai";

    const cacheManager = new GoogleAICacheManager("GOOGLE_API_KEY");
    const fileManager = new GoogleAIFileManager("GOOGLE_API_KEY");

    const uploadResult = await fileManager.uploadFile("path/to/a11.txt", {
      mimeType: "text/plain",
    });

    const cacheResult = await cacheManager.create({
      model: "models/gemini-1.5-flash",
      contents: [
        {
          role: "user",
          parts: [
            {
              fileData: {
                fileUri: uploadResult.file.uri,
                mimeType: uploadResult.file.mimeType,
              },
            },
          ],
        },
      ],
    });

    console.log(cacheResult);

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModelFromCachedContent(cacheResult);
    const result = await model.generateContent(
      "Please summarize this transcript.",
    );
    console.log(result.response.text());

**After**

### Python

    import requests
    import pathlib
    from google import genai
    from google.genai import types

    client = genai.Client()

    # Check which models support caching.
    for m in client.models.list():
      for action in m.supported_actions:
        if action == "createCachedContent":
          print(m.name)
          break

    # Download file
    response = requests.get(
        'https://storage.googleapis.com/generativeai-downloads/data/a11.txt')
    pathlib.Path('a11.txt').write_text(response.text)

    # Upload file
    document = client.files.upload(file='a11.txt')

    # Create cache
    model='gemini-1.5-flash-001'
    apollo_cache = client.caches.create(
          model=model,
          config={
              'contents': [document],
              'system_instruction': 'You are an expert at analyzing transcripts.',
          },
      )

    # Generate response
    response = client.models.generate_content(
        model=model,
        contents='Find a lighthearted moment from this transcript',
        config=types.GenerateContentConfig(
            cached_content=apollo_cache.name,
        )
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const filePath = path.join(media, "a11.txt");
    const document = await ai.files.upload({
      file: filePath,
      config: { mimeType: "text/plain" },
    });
    console.log("Uploaded file name:", document.name);
    const modelName = "gemini-1.5-flash";

    const contents = [
      createUserContent(createPartFromUri(document.uri, document.mimeType)),
    ];

    const cache = await ai.caches.create({
      model: modelName,
      config: {
        contents: contents,
        systemInstruction: "You are an expert analyzing transcripts.",
      },
    });
    console.log("Cache created:", cache);

    const response = await ai.models.generateContent({
      model: modelName,
      contents: "Please summarize this transcript",
      config: { cachedContent: cache.name },
    });
    console.log("Response text:", response.text);

## Count tokens

Count the number of tokens in a request.

**Before**

### Python

    import google.generativeai as genai

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.count_tokens(
        'The quick brown fox jumps over the lazy dog.')

### JavaScript

     import { GoogleGenerativeAI } from "@google/generative-ai";

     const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY+);
     const model = genAI.getGenerativeModel({
       model: "gemini-1.5-flash",
     });

     // Count tokens in a prompt without calling text generation.
     const countResult = await model.countTokens(
       "The quick brown fox jumps over the lazy dog.",
     );

     console.log(countResult.totalTokens); // 11

     const generateResult = await model.generateContent(
       "The quick brown fox jumps over the lazy dog.",
     );

     // On the response for `generateContent`, use `usageMetadata`
     // to get separate input and output token counts
     // (`promptTokenCount` and `candidatesTokenCount`, respectively),
     // as well as the combined token count (`totalTokenCount`).
     console.log(generateResult.response.usageMetadata);
     // candidatesTokenCount and totalTokenCount depend on response, may vary
     // { promptTokenCount: 11, candidatesTokenCount: 124, totalTokenCount: 135 }

**After**

### Python

    from google import genai

    client = genai.Client()

    response = client.models.count_tokens(
        model='gemini-2.0-flash',
        contents='The quick brown fox jumps over the lazy dog.',
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const prompt = "The quick brown fox jumps over the lazy dog.";
    const countTokensResponse = await ai.models.countTokens({
      model: "gemini-2.0-flash",
      contents: prompt,
    });
    console.log(countTokensResponse.totalTokens);

    const generateResponse = await ai.models.generateContent({
      model: "gemini-2.0-flash",
      contents: prompt,
    });
    console.log(generateResponse.usageMetadata);

## Generate images

Generate images:

**Before**

### Python

    #pip install https://github.com/google-gemini/generative-ai-python@imagen
    import google.generativeai as genai

    imagen = genai.ImageGenerationModel(
        "imagen-3.0-generate-001")
    gen_images = imagen.generate_images(
        prompt="Robot holding a red skateboard",
        number_of_images=1,
        safety_filter_level="block_low_and_above",
        person_generation="allow_adult",
        aspect_ratio="3:4",
    )

**After**

### Python

    from google import genai

    client = genai.Client()

    gen_images = client.models.generate_images(
        model='imagen-3.0-generate-001',
        prompt='Robot holding a red skateboard',
        config=types.GenerateImagesConfig(
            number_of_images= 1,
            safety_filter_level= "BLOCK_LOW_AND_ABOVE",
            person_generation= "ALLOW_ADULT",
            aspect_ratio= "3:4",
        )
    )

    for n, image in enumerate(gen_images.generated_images):
        pathlib.Path(f'{n}.png').write_bytes(
            image.image.image_bytes)

## Embed content

Generate content embeddings.

**Before**

### Python

    import google.generativeai as genai

    response = genai.embed_content(
      model='models/gemini-embedding-001',
      content='Hello world'
    )

### JavaScript

    import { GoogleGenerativeAI } from "@google/generative-ai";

    const genAI = new GoogleGenerativeAI("GOOGLE_API_KEY");
    const model = genAI.getGenerativeModel({
      model: "gemini-embedding-001",
    });

    const result = await model.embedContent("Hello world!");

    console.log(result.embedding);

**After**

### Python

    from google import genai

    client = genai.Client()

    response = client.models.embed_content(
      model='gemini-embedding-001',
      contents='Hello world',
    )

### JavaScript

    import {GoogleGenAI} from '@google/genai';

    const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
    const text = "Hello World!";
    const result = await ai.models.embedContent({
      model: "gemini-embedding-001",
      contents: text,
      config: { outputDimensionality: 10 },
    });
    console.log(result.embeddings);

## Tune a Model

Create and use a tuned model.

The new SDK simplifies tuning with `client.tunings.tune`, which launches the
tuning job and polls until the job is complete.

**Before**

### Python

    import google.generativeai as genai
    import random

    # create tuning model
    train_data = {}
    for i in range(1, 6):
      key = f'input {i}'
      value = f'output {i}'
      train_data[key] = value

    name = f'generate-num-{random.randint(0,10000)}'
    operation = genai.create_tuned_model(
        source_model='models/gemini-1.5-flash-001-tuning',
        training_data=train_data,
        id = name,
        epoch_count = 5,
        batch_size=4,
        learning_rate=0.001,
    )
    # wait for tuning complete
    tuningProgress = operation.result()

    # generate content with the tuned model
    model = genai.GenerativeModel(model_name=f'tunedModels/{name}')
    response = model.generate_content('55')

**After**

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    # Check which models are available for tuning.
    for m in client.models.list():
      for action in m.supported_actions:
        if action == "createTunedModel":
          print(m.name)
          break

    # create tuning model
    training_dataset=types.TuningDataset(
            examples=[
                types.TuningExample(
                    text_input=f'input {i}',
                    output=f'output {i}',
                )
                for i in range(5)
            ],
        )
    tuning_job = client.tunings.tune(
        base_model='models/gemini-1.5-flash-001-tuning',
        training_dataset=training_dataset,
        config=types.CreateTuningJobConfig(
            epoch_count= 5,
            batch_size=4,
            learning_rate=0.001,
            tuned_model_display_name="test tuned model"
        )
    )

    # generate content with the tuned model
    response = client.models.generate_content(
        model=tuning_job.tuned_model.model,
        contents='55',
    )

---

# structured-output.md

You can configure Gemini for structured output instead of unstructured text,
allowing precise extraction and standardization of information for further processing.
For example, you can use structured output to extract information from resumes,
standardize them to build a structured database.

Gemini can generate either [JSON](https://ai.google.dev/gemini-api/docs/structured-output#generating-json)
or [enum values](https://ai.google.dev/gemini-api/docs/structured-output#generating-enums) as structured output.

## Generating JSON

To constrain the model to generate JSON, configure a `responseSchema`. The model
will then respond to any prompt with JSON-formatted output.

### Python

    from google import genai
    from pydantic import BaseModel

    class Recipe(BaseModel):
        recipe_name: str
        ingredients: list[str]

    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="List a few popular cookie recipes, and include the amounts of ingredients.",
        config={
            "response_mime_type": "application/json",
            "response_schema": list[Recipe],
        },
    )
    # Use the response as a JSON string.
    print(response.text)

    # Use instantiated objects.
    my_recipes: list[Recipe] = response.parsed

| **Note:** [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/) are not yet supported. If a `pydantic.ValidationError` occurs, it is suppressed, and `.parsed` may be empty/null.

### JavaScript

    import { GoogleGenAI, Type } from "@google/genai";

    const ai = new GoogleGenAI({});

    async function main() {
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents:
          "List a few popular cookie recipes, and include the amounts of ingredients.",
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.ARRAY,
            items: {
              type: Type.OBJECT,
              properties: {
                recipeName: {
                  type: Type.STRING,
                },
                ingredients: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.STRING,
                  },
                },
              },
              propertyOrdering: ["recipeName", "ingredients"],
            },
          },
        },
      });

      console.log(response.text);
    }

    main();

### Go

    package main

    import (
        "context"
        "fmt"
        "log"

        "google.golang.org/genai"
    )

    func main() {
        ctx := context.Background()
        client, err := genai.NewClient(ctx, nil)
        if err != nil {
            log.Fatal(err)
        }

        config := &genai.GenerateContentConfig{
            ResponseMIMEType: "application/json",
            ResponseSchema: &genai.Schema{
                Type: genai.TypeArray,
                Items: &genai.Schema{
                    Type: genai.TypeObject,
                    Properties: map[string]*genai.Schema{
                        "recipeName": {Type: genai.TypeString},
                        "ingredients": {
                            Type:  genai.TypeArray,
                            Items: &genai.Schema{Type: genai.TypeString},
                        },
                    },
                    PropertyOrdering: []string{"recipeName", "ingredients"},
                },
            },
        }

        result, err := client.Models.GenerateContent(
            ctx,
            "gemini-2.5-flash",
            genai.Text("List a few popular cookie recipes, and include the amounts of ingredients."),
            config,
        )
        if err != nil {
            log.Fatal(err)
        }
        fmt.Println(result.Text())
    }

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H 'Content-Type: application/json' \
    -d '{
          "contents": [{
            "parts":[
              { "text": "List a few popular cookie recipes, and include the amounts of ingredients." }
            ]
          }],
          "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
              "type": "ARRAY",
              "items": {
                "type": "OBJECT",
                "properties": {
                  "recipeName": { "type": "STRING" },
                  "ingredients": {
                    "type": "ARRAY",
                    "items": { "type": "STRING" }
                  }
                },
                "propertyOrdering": ["recipeName", "ingredients"]
              }
            }
          }
    }' 2> /dev/null | head

The output might look like this:

    [
      {
        "recipeName": "Chocolate Chip Cookies",
        "ingredients": [
          "1 cup (2 sticks) unsalted butter, softened",
          "3/4 cup granulated sugar",
          "3/4 cup packed brown sugar",
          "1 teaspoon vanilla extract",
          "2 large eggs",
          "2 1/4 cups all-purpose flour",
          "1 teaspoon baking soda",
          "1 teaspoon salt",
          "2 cups chocolate chips"
        ]
      },
      ...
    ]

## Generating enum values

In some cases you might want the model to choose a single option from a list of
options. To implement this behavior, you can pass an _enum_ in your schema. You
can use an enum option anywhere you could use a `string` in the
`responseSchema`, because an enum is an array of strings. Like a JSON schema, an
enum lets you constrain model output to meet the requirements of your
application.

For example, assume that you're developing an application to classify
musical instruments into one of five categories: `"Percussion"`, `"String"`,
`"Woodwind"`, `"Brass"`, or "`"Keyboard"`". You could create an enum to help
with this task.

In the following example, you pass an enum as the
`responseSchema`, constraining the model to choose the most appropriate option.

### Python

    from google import genai
    import enum

    class Instrument(enum.Enum):
      PERCUSSION = "Percussion"
      STRING = "String"
      WOODWIND = "Woodwind"
      BRASS = "Brass"
      KEYBOARD = "Keyboard"

    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='What type of instrument is an oboe?',
        config={
            'response_mime_type': 'text/x.enum',
            'response_schema': Instrument,
        },
    )

    print(response.text)
    # Woodwind

### JavaScript

    import { GoogleGenAI, Type } from "@google/genai";

    const ai = new GoogleGenAI({});

    const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "What type of instrument is an oboe?",
        config: {
          responseMimeType: "text/x.enum",
          responseSchema: {
            type: Type.STRING,
            enum: ["Percussion", "String", "Woodwind", "Brass", "Keyboard"],
          },
        },
      });

    console.log(response.text);

### REST

    curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
        -H 'Content-Type: application/json' \
        -d '{
              "contents": [{
                "parts":[
                  { "text": "What type of instrument is an oboe?" }
                ]
              }],
              "generationConfig": {
                "responseMimeType": "text/x.enum",
                "responseSchema": {
                  "type": "STRING",
                  "enum": ["Percussion", "String", "Woodwind", "Brass", "Keyboard"]
                }
              }
        }'

The Python library will translate the type declarations for the API. However,
the API accepts a subset of the OpenAPI 3.0 schema
([Schema](https://ai.google.dev/api/caching#schema)).

There are two other ways to specify an enumeration. You can use a
[`Literal`](https://docs.pydantic.dev/1.10/usage/types/#literal-type):
\`\`\`

### Python

    Literal["Percussion", "String", "Woodwind", "Brass", "Keyboard"]

And you can also pass the schema as JSON:

### Python

    from google import genai

    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='What type of instrument is an oboe?',
        config={
            'response_mime_type': 'text/x.enum',
            'response_schema': {
                "type": "STRING",
                "enum": ["Percussion", "String", "Woodwind", "Brass", "Keyboard"],
            },
        },
    )

    print(response.text)
    # Woodwind

Beyond basic multiple choice problems, you can use an enum anywhere in a JSON
schema. For example, you could ask the model for a list of recipe titles and
use a `Grade` enum to give each title a popularity grade:

### Python

    from google import genai

    import enum
    from pydantic import BaseModel

    class Grade(enum.Enum):
        A_PLUS = "a+"
        A = "a"
        B = "b"
        C = "c"
        D = "d"
        F = "f"

    class Recipe(BaseModel):
      recipe_name: str
      rating: Grade

    client = genai.Client()
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents='List 10 home-baked cookie recipes and give them grades based on tastiness.',
        config={
            'response_mime_type': 'application/json',
            'response_schema': list[Recipe],
        },
    )

    print(response.text)

The response might look like this:

    [
      {
        "recipe_name": "Chocolate Chip Cookies",
        "rating": "a+"
      },
      {
        "recipe_name": "Peanut Butter Cookies",
        "rating": "a"
      },
      {
        "recipe_name": "Oatmeal Raisin Cookies",
        "rating": "b"
      },
      ...
    ]

## About JSON schemas

Configuring the model for JSON output using `responseSchema` parameter relies on
`Schema` object to define its structure. This object represents a select
subset of the [OpenAPI 3.0 Schema object](https://spec.openapis.org/oas/v3.0.3#schema-object),
and also adds a `propertyOrdering` field.
| **Tip:** On Python, when you use a Pydantic model, you don't need to directly work with `Schema` objects, as it gets automatically converted to the corresponding JSON schema. To learn more, see [JSON schemas in Python](https://ai.google.dev/gemini-api/docs/structured-output#schemas-in-python).

Here's a pseudo-JSON representation of all the `Schema` fields:

    {
      "type": enum (Type),
      "format": string,
      "description": string,
      "nullable": boolean,
      "enum": [
        string
      ],
      "maxItems": integer,
      "minItems": integer,
      "properties": {
        string: {
          object (Schema)
        },
        ...
      },
      "required": [
        string
      ],
      "propertyOrdering": [
        string
      ],
      "items": {
        object (Schema)
      }
    }

The `Type` of the schema must be one of the OpenAPI
[Data Types](https://spec.openapis.org/oas/v3.0.3#data-types), or a union of
those types (using `anyOf`). Only a subset of fields is valid for each `Type`.
The following list maps each `Type` to a subset of the fields that are valid for
that type:

-   `string` -\> `enum`, `format`, `nullable`
-   `integer` -\> `format`, `minimum`, `maximum`, `enum`, `nullable`
-   `number` -\> `format`, `minimum`, `maximum`, `enum`, `nullable`
-   `boolean` -\> `nullable`
-   `array` -\> `minItems`, `maxItems`, `items`, `nullable`
-   `object` -\> `properties`, `required`, `propertyOrdering`, `nullable`

Here are some example schemas showing valid type-and-field combinations:

    { "type": "string", "enum": ["a", "b", "c"] }

    { "type": "string", "format": "date-time" }

    { "type": "integer", "format": "int64" }

    { "type": "number", "format": "double" }

    { "type": "boolean" }

    { "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": ... } }

    { "type": "object",
      "properties": {
        "a": { "type": ... },
        "b": { "type": ... },
        "c": { "type": ... }
      },
      "nullable": true,
      "required": ["c"],
      "propertyOrdering": ["c", "b", "a"]
    }

For complete documentation of the Schema fields as they're used in the Gemini
API, see the [Schema reference](https://ai.google.dev/api/caching#Schema).

### Property ordering

| **Warning:** When you're configuring a JSON schema, make sure to set `propertyOrdering[]`, and when you provide examples, make sure that the property ordering in the examples matches the schema.

When you're working with JSON schemas in the Gemini API, the order of properties
is important. By default, the API orders properties alphabetically and does not
preserve the order in which the properties are defined (although the
[Google Gen AI SDKs](https://ai.google.dev/gemini-api/docs/sdks) may preserve this order). If you're
providing examples to the model with a schema configured, and the property
ordering of the examples is not consistent with the property ordering of the
schema, the output could be rambling or unexpected.

To ensure a consistent, predictable ordering of properties, you can use the
optional `propertyOrdering[]` field.

    "propertyOrdering": ["recipeName", "ingredients"]

`propertyOrdering[]` -- not a standard field in the OpenAPI specification
-- is an array of strings used to determine the order of properties in the
response. By specifying the order of properties and then providing examples with
properties in that same order, you can potentially improve the quality of
results. `propertyOrdering` is only supported when you manually create
`types.Schema`.

### Schemas in Python

When you're using the Python library, the value of `response_schema` must be one
of the following:

-   A type, as you would use in a type annotation (see the Python [`typing` module](https://docs.python.org/3/library/typing.html))
-   An instance of [`genai.types.Schema`](https://googleapis.github.io/python-genai/genai.html#genai.types.Schema)
-   The `dict` equivalent of `genai.types.Schema`

The easiest way to define a schema is with a Pydantic type (as shown in the
previous example):

### Python

    config={'response_mime_type': 'application/json',
            'response_schema': list[Recipe]}

When you use a Pydantic type, the Python library builds out a JSON schema for
you and sends it to the API. For additional examples, see the
[Python library docs](https://googleapis.github.io/python-genai/index.html#json-response-schema).

The Python library supports schemas defined with the following types (where
`AllowedType` is any allowed type):

-   `int`
-   `float`
-   `bool`
-   `str`
-   `list[AllowedType]`
-   `AllowedType|AllowedType|...`
-   For structured types:
    -   `dict[str, AllowedType]`. This annotation declares all dict values to be the same type, but doesn't specify what keys should be included.
    -   User-defined [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/). This approach lets you specify the key names and define different types for the values associated with each of the keys, including nested structures.

### JSON Schema support

[JSON Schema](https://json-schema.org/) is a more recent specification than
OpenAPI 3.0, which the [Schema](https://ai.google.dev/api/caching#Schema) object is based on.
Support for JSON Schema is available as a preview using the field
[`responseJsonSchema`](https://ai.google.dev/api/generate-content#FIELDS.response_json_schema) which
accepts any JSON Schema with the following limitations:

-   It only works with Gemini 2.5.
-   While all JSON Schema properties can be passed, not all are supported. See the [documentation](https://ai.google.dev/api/generate-content#FIELDS.response_json_schema) for the field for more details.
-   Recursive references can only be used as the value of a non-required object property.
-   Recursive references are unrolled to a finite degree, based on the size of the schema.
-   Schemas that contain `$ref` cannot contain any properties other than those starting with a `$`.

Here's an example of generating a JSON Schema with Pydantic and submitting it to
the model:

    curl "https://generativelanguage.googleapis.com/v1alpha/models/\
    gemini-2.5-flash:generateContent" \
        -H "x-goog-api-key: $GEMINI_API_KEY"\
        -H 'Content-Type: application/json' \
        -d @- <<EOF
    {
      "contents": [{
        "parts":[{
          "text": "Please give a random example following this schema"
        }]
      }],
      "generationConfig": {
        "response_mime_type": "application/json",
        "response_json_schema": $(python3 - << PYEOF
        from enum import Enum
        from typing import List, Optional, Union, Set
        from pydantic import BaseModel, Field, ConfigDict
        import json

        class UserRole(str, Enum):
            ADMIN = "admin"
            VIEWER = "viewer"

        class Address(BaseModel):
            street: str
            city: str

        class UserProfile(BaseModel):
            username: str = Field(description="User's unique name")
            age: Optional[int] = Field(ge=0, le=120)
            roles: Set[UserRole] = Field(min_items=1)
            contact: Union[Address, str]
            model_config = ConfigDict(title="User Schema")

        # Generate and print the JSON Schema
        print(json.dumps(UserProfile.model_json_schema(), indent=2))
        PYEOF
        )
      }
    }
    EOF

Passing JSON Schema directly is not yet supported when using the SDK.

## Best practices

Keep the following considerations and best practices in mind when you're using a
response schema:

-   The size of your response schema counts towards the input token limit.
-   By default, fields are optional, meaning the model can populate the fields or skip them. You can set fields as required to force the model to provide a value. If there's insufficient context in the associated input prompt, the model generates responses mainly based on the data it was trained on.
-   A complex schema can result in an `InvalidArgument: 400` error. Complexity
    might come from long property names, long array length limits, enums with
    many values, objects with lots of optional properties, or a combination of
    these factors.

    If you get this error with a valid schema, make one or more of the following
    changes to resolve the error:

    -   Shorten property names or enum names.
    -   Flatten nested arrays.
    -   Reduce the number of properties with constraints, such as numbers with minimum and maximum limits.
    -   Reduce the number of properties with complex constraints, such as properties with complex formats like `date-time`.
    -   Reduce the number of optional properties.
    -   Reduce the number of valid values for enums.

-   If you aren't seeing the results you expect, add more context to your input
    prompts or revise your response schema. For example, review the model's
    response without structured output to see how the model responds. You can then
    update your response schema so that it better fits the model's output.
    For additional troubleshooting tips on structured output, see the
    [troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting#repetitive-tokens).

## What's next

Now that you've learned how to generate structured output, you might want to try
using Gemini API tools:

-   [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
-   [Code execution](https://ai.google.dev/gemini-api/docs/code-execution)
-   [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/grounding)

---

# batch-api.md

The Gemini Batch API is designed to process large volumes of requests
asynchronously at [50% of the standard cost](https://ai.google.dev/gemini-api/docs/pricing).
The target turnaround time is 24 hours, but in majority of cases, it is much
quicker.

Use Batch API for large-scale, non-urgent tasks such as data
pre-processing or running evaluations where an immediate response is not
required.

## Creating a batch job

You have two ways to submit your requests in Batch API:

-   **[Inline Requests](https://ai.google.dev/gemini-api/docs/batch-api#inline-requests):** A list of [`GenerateContentRequest`](https://ai.google.dev/api/batch-mode#GenerateContentRequest) objects directly included in your batch creation request. This is suitable for smaller batches that keep the total request size under 20MB. The **output** returned from the model is a list of `inlineResponse` objects.
-   **[Input File](https://ai.google.dev/gemini-api/docs/batch-api#input-file):** A [JSON Lines (JSONL)](https://jsonlines.org/) file where each line contains a complete [`GenerateContentRequest`](https://ai.google.dev/api/batch-mode#GenerateContentRequest) object. This method is recommended for larger requests. The **output** returned from the model is a JSONL file where each line is either a `GenerateContentResponse` or a status object.

### Inline requests

For a small number of requests, you can directly embed the
[`GenerateContentRequest`](https://ai.google.dev/api/batch-mode#GenerateContentRequest) objects
within your [`BatchGenerateContentRequest`](https://ai.google.dev/api/batch-mode#request-body). The
following example calls the
[`BatchGenerateContent`](https://ai.google.dev/api/batch-mode#google.ai.generativelanguage.v1beta.BatchService.BatchGenerateContent)
method with inline requests:

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    # A list of dictionaries, where each is a GenerateContentRequest
    inline_requests = [
        {
            'contents': [{
                'parts': [{'text': 'Tell me a one-sentence joke.'}],
                'role': 'user'
            }]
        },
        {
            'contents': [{
                'parts': [{'text': 'Why is the sky blue?'}],
                'role': 'user'
            }]
        }
    ]

    inline_batch_job = client.batches.create(
        model="models/gemini-2.5-flash",
        src=inline_requests,
        config={
            'display_name': "inlined-requests-job-1",
        },
    )

    print(f"Created batch job: {inline_batch_job.name}")

### JavaScript

    import {GoogleGenAI} from '@google/genai';
    const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

    const ai = new GoogleGenAI({apiKey: GEMINI_API_KEY});

    const inlinedRequests = [
        {
            contents: [{
                parts: [{text: 'Tell me a one-sentence joke.'}],
                role: 'user'
            }]
        },
        {
            contents: [{
                parts: [{'text': 'Why is the sky blue?'}],
                role: 'user'
            }]
        }
    ]

    const response = await ai.batches.create({
        model: 'gemini-2.5-flash',
        src: inlinedRequests,
        config: {
            displayName: 'inlined-requests-job-1',
        }
    });

    console.log(response);

### REST

    curl https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:batchGenerateContent \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -X POST \
    -H "Content-Type:application/json" \
    -d '{
        "batch": {
            "display_name": "my-batch-requests",
            "input_config": {
                "requests": {
                    "requests": [
                        {
                            "request": {"contents": [{"parts": [{"text": "Describe the process of photosynthesis."}]}]},
                            "metadata": {
                                "key": "request-1"
                            }
                        },
                        {
                            "request": {"contents": [{"parts": [{"text": "Describe the process of photosynthesis."}]}]},
                            "metadata": {
                                "key": "request-2"
                            }
                        }
                    ]
                }
            }
        }
    }'

### Input file

For larger sets of requests, prepare a JSON Lines (JSONL) file. Each line in
this file must be a JSON object containing a user-defined key and a request
object, where the request is a valid
[`GenerateContentRequest`](https://ai.google.dev/api/batch-mode#GenerateContentRequest) object. The
user-defined key is used in the response to indicate which output is the result
of which request. For example, the request with the key defined as `request-1`
will have its response annotated with the same key name.

This file is uploaded using the [File API](https://ai.google.dev/gemini-api/docs/files). The maximum
allowed file size for an input file is 2GB.

The following is an example of a JSONL file. You can save it in a file named
`my-batch-requests.json`:

    {"key": "request-1", "request": {"contents": [{"parts": [{"text": "Describe the process of photosynthesis."}]}], "generation_config": {"temperature": 0.7}}}
    {"key": "request-2", "request": {"contents": [{"parts": [{"text": "What are the main ingredients in a Margherita pizza?"}]}]}}

Similarly to inline requests, you can specify other parameters like system
instructions, tools or other configurations in each request JSON.

You can upload this file using the [File API](https://ai.google.dev/gemini-api/docs/files) as
shown in the following example. If
you are working with multimodal input, you can reference other uploaded files
within your JSONL file.

### Python

    import json
    from google import genai
    from google.genai import types

    client = genai.Client()

    # Create a sample JSONL file
    with open("my-batch-requests.jsonl", "w") as f:
        requests = [
            {"key": "request-1", "request": {"contents": [{"parts": [{"text": "Describe the process of photosynthesis."}]}]}},
            {"key": "request-2", "request": {"contents": [{"parts": [{"text": "What are the main ingredients in a Margherita pizza?"}]}]}}
        ]
        for req in requests:
            f.write(json.dumps(req) + "\n")

    # Upload the file to the File API
    uploaded_file = client.files.upload(
        file='my-batch-requests.jsonl',
        config=types.UploadFileConfig(display_name='my-batch-requests', mime_type='jsonl')
    )

    print(f"Uploaded file: {uploaded_file.name}")

### JavaScript

    import {GoogleGenAI} from '@google/genai';
    import * as fs from "fs";
    import * as path from "path";
    import { fileURLToPath } from 'url';

    const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
    const ai = new GoogleGenAI({apiKey: GEMINI_API_KEY});
    const fileName = "my-batch-requests.jsonl";

    // Define the requests
    const requests = [
        { "key": "request-1", "request": { "contents": [{ "parts": [{ "text": "Describe the process of photosynthesis." }] }] } },
        { "key": "request-2", "request": { "contents": [{ "parts": [{ "text": "What are the main ingredients in a Margherita pizza?" }] }] } }
    ];

    // Construct the full path to file
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const filePath = path.join(__dirname, fileName); // __dirname is the directory of the current script

    async function writeBatchRequestsToFile(requests, filePath) {
        try {
            // Use a writable stream for efficiency, especially with larger files.
            const writeStream = fs.createWriteStream(filePath, { flags: 'w' });

            writeStream.on('error', (err) => {
                console.error(`Error writing to file ${filePath}:`, err);
            });

            for (const req of requests) {
                writeStream.write(JSON.stringify(req) + '\n');
            }

            writeStream.end();

            console.log(`Successfully wrote batch requests to ${filePath}`);

        } catch (error) {
            // This catch block is for errors that might occur before stream setup,
            // stream errors are handled by the 'error' event.
            console.error(`An unexpected error occurred:`, error);
        }
    }

    // Write to a file.
    writeBatchRequestsToFile(requests, filePath);

    // Upload the file to the File API.
    const uploadedFile = await ai.files.upload({file: 'my-batch-requests.jsonl', config: {
        mimeType: 'jsonl',
    }});
    console.log(uploadedFile.name);

### REST

    tmp_batch_input_file=batch_input.tmp
    echo -e '{"contents": [{"parts": [{"text": "Describe the process of photosynthesis."}]}], "generationConfig": {"temperature": 0.7}}\n{"contents": [{"parts": [{"text": "What are the main ingredients in a Margherita pizza?"}]}]}' > batch_input.tmp
    MIME_TYPE=$(file -b --mime-type "${tmp_batch_input_file}")
    NUM_BYTES=$(wc -c < "${tmp_batch_input_file}")
    DISPLAY_NAME=BatchInput

    tmp_header_file=upload-header.tmp

    # Initial resumable request defining metadata.
    # The upload url is in the response headers dump them to a file.
    curl "https://generativelanguage.googleapis.com/upload/v1beta/files" \
    -D "${tmp_header_file}" \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H "X-Goog-Upload-Protocol: resumable" \
    -H "X-Goog-Upload-Command: start" \
    -H "X-Goog-Upload-Header-Content-Length: ${NUM_BYTES}" \
    -H "X-Goog-Upload-Header-Content-Type: ${MIME_TYPE}" \
    -H "Content-Type: application/jsonl" \
    -d "{'file': {'display_name': '${DISPLAY_NAME}'}}" 2> /dev/null

    upload_url=$(grep -i "x-goog-upload-url: " "${tmp_header_file}" | cut -d" " -f2 | tr -d "\r")
    rm "${tmp_header_file}"

    # Upload the actual bytes.
    curl "${upload_url}" \
    -H "Content-Length: ${NUM_BYTES}" \
    -H "X-Goog-Upload-Offset: 0" \
    -H "X-Goog-Upload-Command: upload, finalize" \
    --data-binary "@${tmp_batch_input_file}" 2> /dev/null > file_info.json

    file_uri=$(jq ".file.uri" file_info.json)

The following example calls the
[`BatchGenerateContent`](https://ai.google.dev/api/batch-mode#google.ai.generativelanguage.v1beta.BatchService.BatchGenerateContent)
method with the input file uploaded using File API:

### Python

    from google import genai

    # Assumes `uploaded_file` is the file object from the previous step
    client = genai.Client()
    file_batch_job = client.batches.create(
        model="gemini-2.5-flash",
        src=uploaded_file.name,
        config={
            'display_name': "file-upload-job-1",
        },
    )

    print(f"Created batch job: {file_batch_job.name}")

### JavaScript

    // Assumes `uploadedFile` is the file object from the previous step
    const fileBatchJob = await ai.batches.create({
        model: 'gemini-2.5-flash',
        src: uploadedFile.name,
        config: {
            displayName: 'file-upload-job-1',
        }
    });

    console.log(fileBatchJob);

### REST

    # Set the File ID taken from the upload response.
    BATCH_INPUT_FILE='files/123456'
    curl https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:batchGenerateContent \
    -X POST \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H "Content-Type:application/json" \
    -d "{
        'batch': {
            'display_name': 'my-batch-requests',
            'input_config': {
                'file_name': '${BATCH_INPUT_FILE}'
            }
        }
    }"

When you create a batch job, you will get a job name returned. Use this name
for [monitoring](https://ai.google.dev/gemini-api/docs/batch-api#batch-job-status) the job status as well as
[retrieving the results](https://ai.google.dev/gemini-api/docs/batch-api#retrieve-batch-results) once the job completes.

The following is an example output that contains a job name:

    Created batch job from file: batches/123456789

### Batch embedding support

You can use the Batch API to interact with the
[Embeddings model](https://ai.google.dev/gemini-api/docs/embeddings) for higher throughput.
To create an embeddings batch job with either [inline requests](https://ai.google.dev/gemini-api/docs/batch-api#inline-requests)
or [input files](https://ai.google.dev/gemini-api/docs/batch-api#input-file), use the `batches.create_embeddings` API and
specify the embeddings model.

### Python

    from google import genai

    client = genai.Client()

    # Creating an embeddings batch job with an input file request:
    file_job = client.batches.create_embeddings(
        model="gemini-embedding-001",
        src={'file_name': uploaded_batch_requests.name},
        config={'display_name': "Input embeddings batch"},
    )

    # Creating an embeddings batch job with an inline request:
    batch_job = client.batches.create_embeddings(
        model="gemini-embedding-001",
        # For a predefined list of requests `inlined_requests`
        src={'inlined_requests': inlined_requests},
        config={'display_name': "Inlined embeddings batch"},
    )

### JavaScript

    // Creating an embeddings batch job with an input file request:
    let fileJob;
    fileJob = await client.batches.createEmbeddings({
        model: 'gemini-embedding-001',
        src: {fileName: uploadedBatchRequests.name},
        config: {displayName: 'Input embeddings batch'},
    });
    console.log(`Created batch job: ${fileJob.name}`);

    // Creating an embeddings batch job with an inline request:
    let batchJob;
    batchJob = await client.batches.createEmbeddings({
        model: 'gemini-embedding-001',
        // For a predefined a list of requests `inlinedRequests`
        src: {inlinedRequests: inlinedRequests},
        config: {displayName: 'Inlined embeddings batch'},
    });
    console.log(`Created batch job: ${batchJob.name}`);

Read the Embeddings section in the [Batch API cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Batch_mode.ipynb)
for more examples.

### Request configuration

You can include any request configurations you would use in a standard non-batch
request. For example, you could specify the temperature, system instructions or
even pass in other modalities. The following example shows an example inline
request that contains a system instruction for one of the requests:

### Python

    inline_requests_list = [
        {'contents': [{'parts': [{'text': 'Write a short poem about a cloud.'}]}]},
        {'contents': [{'parts': [{'text': 'Write a short poem about a cat.'}]}], 'system_instructions': {'parts': [{'text': 'You are a cat. Your name is Neko.'}]}}
    ]

### JavaScript

    inlineRequestsList = [
        {contents: [{parts: [{text: 'Write a short poem about a cloud.'}]}]},
        {contents: [{parts: [{text: 'Write a short poem about a cat.'}]}], systemInstructions: {parts: [{text: 'You are a cat. Your name is Neko.'}]}}
    ]

Similarly can specify tools to use for a request. The following example
shows a request that enables the [Google Search tool](https://ai.google.dev/gemini-api/docs/google-search):

### Python

    inline_requests_list = [
        {'contents': [{'parts': [{'text': 'Who won the euro 1998?'}]}]},
        {'contents': [{'parts': [{'text': 'Who won the euro 2025?'}]}], 'tools': [{'google_search ': {}}]}
    ]

### JavaScript

    inlineRequestsList = [
        {contents: [{parts: [{text: 'Who won the euro 1998?'}]}]},
        {contents: [{parts: [{text: 'Who won the euro 2025?'}]}], tools: [{googleSearch: {}}]}
    ]

You can specify [structured output](https://ai.google.dev/gemini-api/docs/structured-output) as well.
The following example shows how to specify for your batch requests.

### Python

    import time
    from google import genai
    from pydantic import BaseModel, TypeAdapter

    class Recipe(BaseModel):
        recipe_name: str
        ingredients: list[str]

    client = genai.Client()

    # A list of dictionaries, where each is a GenerateContentRequest
    inline_requests = [
        {
            'contents': [{
                'parts': [{'text': 'List a few popular cookie recipes, and include the amounts of ingredients.'}],
                'role': 'user'
            }],
            'config': {
                'response_mime_type': 'application/json',
                'response_schema': list[Recipe]
            }
        },
        {
            'contents': [{
                'parts': [{'text': 'List a few popular gluten free cookie recipes, and include the amounts of ingredients.'}],
                'role': 'user'
            }],
            'config': {
                'response_mime_type': 'application/json',
                'response_schema': list[Recipe]
            }
        }
    ]

    inline_batch_job = client.batches.create(
        model="models/gemini-2.5-flash",
        src=inline_requests,
        config={
            'display_name': "structured-output-job-1"
        },
    )

    # wait for the job to finish
    job_name = inline_batch_job.name
    print(f"Polling status for job: {job_name}")

    while True:
        batch_job_inline = client.batches.get(name=job_name)
        if batch_job_inline.state.name in ('JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED'):
            break
        print(f"Job not finished. Current state: {batch_job_inline.state.name}. Waiting 30 seconds...")
        time.sleep(30)

    print(f"Job finished with state: {batch_job_inline.state.name}")

    # print the response
    for i, inline_response in enumerate(batch_job_inline.dest.inlined_responses, start=1):
        print(f"\n--- Response {i} ---")

        # Check for a successful response
        if inline_response.response:
            # The .text property is a shortcut to the generated text.
            print(inline_response.response.text)

### JavaScript

    import {GoogleGenAI, Type} from '@google/genai';
    const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

    const ai = new GoogleGenAI({apiKey: GEMINI_API_KEY});

    const inlinedRequests = [
        {
            contents: [{
                parts: [{text: 'List a few popular cookie recipes, and include the amounts of ingredients.'}],
                role: 'user'
            }],
            config: {
                responseMimeType: 'application/json',
                responseSchema: {
                type: Type.ARRAY,
                items: {
                    type: Type.OBJECT,
                    properties: {
                    'recipeName': {
                        type: Type.STRING,
                        description: 'Name of the recipe',
                        nullable: false,
                    },
                    'ingredients': {
                        type: Type.ARRAY,
                        items: {
                        type: Type.STRING,
                        description: 'Ingredients of the recipe',
                        nullable: false,
                        },
                    },
                    },
                    required: ['recipeName'],
                },
                },
            }
        },
        {
            contents: [{
                parts: [{text: 'List a few popular gluten free cookie recipes, and include the amounts of ingredients.'}],
                role: 'user'
            }],
            config: {
                responseMimeType: 'application/json',
                responseSchema: {
                type: Type.ARRAY,
                items: {
                    type: Type.OBJECT,
                    properties: {
                    'recipeName': {
                        type: Type.STRING,
                        description: 'Name of the recipe',
                        nullable: false,
                    },
                    'ingredients': {
                        type: Type.ARRAY,
                        items: {
                        type: Type.STRING,
                        description: 'Ingredients of the recipe',
                        nullable: false,
                        },
                    },
                    },
                    required: ['recipeName'],
                },
                },
            }
        }
    ]

    const inlinedBatchJob = await ai.batches.create({
        model: 'gemini-2.5-flash',
        src: inlinedRequests,
        config: {
            displayName: 'inlined-requests-job-1',
        }
    });

## Monitoring job status

Use the operation name obtained when creating the batch job to poll its status.
The state field of the batch job will indicate its current status. A batch job
can be in one of the following states:

-   `JOB_STATE_PENDING`: The job has been created and is waiting to be processed by the service.
-   `JOB_STATE_RUNNING`: The job is in progress.
-   `JOB_STATE_SUCCEEDED`: The job completed successfully. You can now retrieve the results.
-   `JOB_STATE_FAILED`: The job failed. Check the error details for more information.
-   `JOB_STATE_CANCELLED`: The job was cancelled by the user.
-   `JOB_STATE_EXPIRED`: The job has expired because it was running or pending for more than 48 hours. The job will not have any results to retrieve. You can try submitting the job again or splitting up the requests into smaller batches.

You can poll the job status periodically to check for completion.

### Python

    import time
    from google import genai

    client = genai.Client()

    # Use the name of the job you want to check
    # e.g., inline_batch_job.name from the previous step
    job_name = "YOUR_BATCH_JOB_NAME"  # (e.g. 'batches/your-batch-id')
    batch_job = client.batches.get(name=job_name)

    completed_states = set([
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
    ])

    print(f"Polling status for job: {job_name}")
    batch_job = client.batches.get(name=job_name) # Initial get
    while batch_job.state.name not in completed_states:
      print(f"Current state: {batch_job.state.name}")
      time.sleep(30) # Wait for 30 seconds before polling again
      batch_job = client.batches.get(name=job_name)

    print(f"Job finished with state: {batch_job.state.name}")
    if batch_job.state.name == 'JOB_STATE_FAILED':
        print(f"Error: {batch_job.error}")

### JavaScript

    // Use the name of the job you want to check
    // e.g., inlinedBatchJob.name from the previous step
    let batchJob;
    const completedStates = new Set([
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
    ]);

    try {
        batchJob = await ai.batches.get({name: inlinedBatchJob.name});
        while (!completedStates.has(batchJob.state)) {
            console.log(`Current state: ${batchJob.state}`);
            // Wait for 30 seconds before polling again
            await new Promise(resolve => setTimeout(resolve, 30000));
            batchJob = await client.batches.get({ name: batchJob.name });
        }
        console.log(`Job finished with state: ${batchJob.state}`);
        if (batchJob.state === 'JOB_STATE_FAILED') {
            // The exact structure of `error` might vary depending on the SDK
            // This assumes `error` is an object with a `message` property.
            console.error(`Error: ${batchJob.state}`);
        }
    } catch (error) {
        console.error(`An error occurred while polling job ${batchJob.name}:`, error);
    }

## Retrieving results

Once the job status indicates your batch job has succeeded, the results are
available in the `response` field.

### Python

    import json
    from google import genai

    client = genai.Client()

    # Use the name of the job you want to check
    # e.g., inline_batch_job.name from the previous step
    job_name = "YOUR_BATCH_JOB_NAME"
    batch_job = client.batches.get(name=job_name)

    if batch_job.state.name == 'JOB_STATE_SUCCEEDED':

        # If batch job was created with a file
        if batch_job.dest and batch_job.dest.file_name:
            # Results are in a file
            result_file_name = batch_job.dest.file_name
            print(f"Results are in file: {result_file_name}")

            print("Downloading result file content...")
            file_content = client.files.download(file=result_file_name)
            # Process file_content (bytes) as needed
            print(file_content.decode('utf-8'))

        # If batch job was created with inline request
        # (for embeddings, use batch_job.dest.inlined_embed_content_responses)
        elif batch_job.dest and batch_job.dest.inlined_responses:
            # Results are inline
            print("Results are inline:")
            for i, inline_response in enumerate(batch_job.dest.inlined_responses):
                print(f"Response {i+1}:")
                if inline_response.response:
                    # Accessing response, structure may vary.
                    try:
                        print(inline_response.response.text)
                    except AttributeError:
                        print(inline_response.response) # Fallback
                elif inline_response.error:
                    print(f"Error: {inline_response.error}")
        else:
            print("No results found (neither file nor inline).")
    else:
        print(f"Job did not succeed. Final state: {batch_job.state.name}")
        if batch_job.error:
            print(f"Error: {batch_job.error}")

### JavaScript

    // Use the name of the job you want to check
    // e.g., inlinedBatchJob.name from the previous step
    const jobName = "YOUR_BATCH_JOB_NAME";

    try {
        const batchJob = await ai.batches.get({ name: jobName });

        if (batchJob.state === 'JOB_STATE_SUCCEEDED') {
            console.log('Found completed batch:', batchJob.displayName);
            console.log(batchJob);

            // If batch job was created with a file destination
            if (batchJob.dest?.fileName) {
                const resultFileName = batchJob.dest.fileName;
                console.log(`Results are in file: ${resultFileName}`);

                console.log("Downloading result file content...");
                const fileContentBuffer = await ai.files.download({ file: resultFileName });

                // Process fileContentBuffer (Buffer) as needed
                console.log(fileContentBuffer.toString('utf-8'));
            }

            // If batch job was created with inline responses
            else if (batchJob.dest?.inlinedResponses) {
                console.log("Results are inline:");
                for (let i = 0; i < batchJob.dest.inlinedResponses.length; i++) {
                    const inlineResponse = batchJob.dest.inlinedResponses[i];
                    console.log(`Response ${i + 1}:`);
                    if (inlineResponse.response) {
                        // Accessing response, structure may vary.
                        if (inlineResponse.response.text !== undefined) {
                            console.log(inlineResponse.response.text);
                        } else {
                            console.log(inlineResponse.response); // Fallback
                        }
                    } else if (inlineResponse.error) {
                        console.error(`Error: ${inlineResponse.error}`);
                    }
                }
            }

            // If batch job was an embedding batch with inline responses
            else if (batchJob.dest?.inlinedEmbedContentResponses) {
                console.log("Embedding results found inline:");
                for (let i = 0; i < batchJob.dest.inlinedEmbedContentResponses.length; i++) {
                    const inlineResponse = batchJob.dest.inlinedEmbedContentResponses[i];
                    console.log(`Response ${i + 1}:`);
                    if (inlineResponse.response) {
                        console.log(inlineResponse.response);
                    } else if (inlineResponse.error) {
                        console.error(`Error: ${inlineResponse.error}`);
                    }
                }
            } else {
                console.log("No results found (neither file nor inline).");
            }
        } else {
            console.log(`Job did not succeed. Final state: ${batchJob.state}`);
            if (batchJob.error) {
                console.error(`Error: ${typeof batchJob.error === 'string' ? batchJob.error : batchJob.error.message || JSON.stringify(batchJob.error)}`);
            }
        }
    } catch (error) {
        console.error(`An error occurred while processing job ${jobName}:`, error);
    }

### REST

    BATCH_NAME="batches/123456" # Your batch job name

    curl https://generativelanguage.googleapis.com/v1beta/$BATCH_NAME \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H "Content-Type:application/json" 2> /dev/null > batch_status.json

    if jq -r '.done' batch_status.json | grep -q "false"; then
        echo "Batch has not finished processing"
    fi

    batch_state=$(jq -r '.metadata.state' batch_status.json)
    if [[ $batch_state = "JOB_STATE_SUCCEEDED" ]]; then
        if [[ $(jq '.response | has("inlinedResponses")' batch_status.json) = "true" ]]; then
            jq -r '.response.inlinedResponses' batch_status.json
            exit
        fi
        responses_file_name=$(jq -r '.response.responsesFile' batch_status.json)
        curl https://generativelanguage.googleapis.com/download/v1beta/$responses_file_name:download?alt=media \
        -H "x-goog-api-key: $GEMINI_API_KEY" 2> /dev/null
    elif [[ $batch_state = "JOB_STATE_FAILED" ]]; then
        jq '.error' batch_status.json
    elif [[ $batch_state == "JOB_STATE_CANCELLED" ]]; then
        echo "Batch was cancelled by the user"
    elif [[ $batch_state == "JOB_STATE_EXPIRED" ]]; then
        echo "Batch expired after 48 hours"
    fi

## Cancelling a batch job

You can cancel an ongoing batch job using its name. When a job is
canceled, it stops processing new requests.

### Python

    from google import genai

    client = genai.Client()

    # Cancel a batch job
    client.batches.cancel(name=batch_job_to_cancel.name)

### JavaScript

    await ai.batches.cancel({name: batchJobToCancel.name});

### REST

    BATCH_NAME="batches/123456" # Your batch job name

    # Cancel the batch
    curl https://generativelanguage.googleapis.com/v1beta/$BATCH_NAME:cancel \
    -H "x-goog-api-key: $GEMINI_API_KEY" \

    # Confirm that the status of the batch after cancellation is JOB_STATE_CANCELLED
    curl https://generativelanguage.googleapis.com/v1beta/$BATCH_NAME \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H "Content-Type:application/json" 2> /dev/null | jq -r '.metadata.state'

## Deleting a batch job

You can delete an existing batch job using its name. When a job is
deleted, it stops processing new requests and is removed from the list of
batch jobs.

### Python

    from google import genai

    client = genai.Client()

    # Delete a batch job
    client.batches.delete(name=batch_job_to_delete.name)

### JavaScript

    await ai.batches.delete({name: batchJobToDelete.name});

### REST

    BATCH_NAME="batches/123456" # Your batch job name

    # Delete the batch job
    curl https://generativelanguage.googleapis.com/v1beta/$BATCH_NAME:delete \
    -H "x-goog-api-key: $GEMINI_API_KEY"

## Technical details

-   **Supported models:** Batch API supports a range of Gemini models. Refer to the [Models page](https://ai.google.dev/gemini-api/docs/models) for each model's support of Batch API. The supported modalities for Batch API are the same as what's supported on the interactive (or non-batch) API.
-   **Pricing:** Batch API usage is priced at 50% of the standard interactive API cost for the equivalent model. See the [pricing page](https://ai.google.dev/gemini-api/docs/pricing) for details. Refer to the [rate limits page](https://ai.google.dev/gemini-api/docs/rate-limits#batch-mode) for details on rate limits for this feature.
-   **Service Level Objective (SLO):** Batch jobs are designed to complete within a 24-hour turnaround time. Many jobs may complete much faster depending on their size and current system load.
-   **Caching:** [Context caching](https://ai.google.dev/gemini-api/docs/caching) is enabled for batch requests. If a request in your batch results in a cache hit, the cached tokens are priced the same as for non-batch API traffic.

## Best practices

-   **Use input files for large requests:** For a large number of requests, always use the file input method for better manageability and to avoid hitting request size limits for the [`BatchGenerateContent`](https://ai.google.dev/api/batch-mode#google.ai.generativelanguage.v1beta.BatchService.BatchGenerateContent) call itself. Note that there's a the 2GB file size limit per input file.
-   **Error handling:** Check the `batchStats` for `failedRequestCount` after a job completes. If using file output, parse each line to check if it's a `GenerateContentResponse` or a status object indicating an error for that specific request. See the [troubleshooting
    guide](https://ai.google.dev/gemini-api/docs/troubleshooting#error-codes) for a complete set of error codes.
-   **Submit jobs once:** The creation of a batch job is not idempotent. If you send the same creation request twice, two separate batch jobs will be created.
-   **Break up very large batches:** While the target turnaround time is 24 hours, actual processing time can vary based on system load and job size. For large jobs, consider breaking them into smaller batches if intermediate results are needed sooner.

## What's next

-   Check out the [Batch API notebook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Batch_mode.ipynb) for more examples.
-   The OpenAI compatibility layer supports Batch API. Read the examples on the [OpenAI Compatibility](https://ai.google.dev/gemini-api/docs/openai#batch) page.

---

# caching.md

Python JavaScript Go REST

In a typical AI workflow, you might pass the same input tokens over and over to
a model. The Gemini API offers two different caching mechanisms:

-   Implicit caching (automatically enabled on Gemini 2.5 models, no cost saving guarantee)
-   Explicit caching (can be manually enabled on most models, cost saving guarantee)

Explicit caching is useful in cases where you want to guarantee cost savings,
but with some added developer work.

## Implicit caching

Implicit caching is enabled by default for all Gemini 2.5 models. We automatically
pass on cost savings if your request hits caches. There is nothing you need to do
in order to enable this. It is effective as of May 8th, 2025. The minimum input
token count for context caching is 1,024 for 2.5 Flash and 4,096 for 2.5 Pro.

To increase the chance of an implicit cache hit:

-   Try putting large and common contents at the beginning of your prompt
-   Try to send requests with similar prefix in a short amount of time

You can see the number of tokens which were cache hits in the response object's
`usage_metadata` field.

## Explicit caching

Using the Gemini API explicit caching feature, you can pass some content
to the model once, cache the input tokens, and then refer to the cached tokens
for subsequent requests. At certain volumes, using cached tokens is lower cost
than passing in the same corpus of tokens repeatedly.

When you cache a set of tokens, you can choose how long you want the cache to
exist before the tokens are automatically deleted. This caching duration is
called the _time to live_ (TTL). If not set, the TTL defaults to 1 hour. The
cost for caching depends on the input token size and how long you want the
tokens to persist.

This section assumes that you've installed a Gemini SDK (or have curl installed)
and that you've configured an API key, as shown in the
[quickstart](https://ai.google.dev/gemini-api/docs/quickstart).

### Generate content using a cache

The following example shows how to generate content using a cached system
instruction and video file.

### Videos

    import os
    import pathlib
    import requests
    import time

    from google import genai
    from google.genai import types

    client = genai.Client()

    # Download video file
    url = 'https://storage.googleapis.com/generativeai-downloads/data/SherlockJr._10min.mp4'
    path_to_video_file = pathlib.Path('SherlockJr._10min.mp4')
    if not path_to_video_file.exists():
      with path_to_video_file.open('wb') as wf:
        response = requests.get(url, stream=True)
        for chunk in response.iter_content(chunk_size=32768):
          wf.write(chunk)

    # Upload the video using the Files API
    video_file = client.files.upload(file=path_to_video_file)

    # Wait for the file to finish processing
    while video_file.state.name == 'PROCESSING':
      print('Waiting for video to be processed.')
      time.sleep(2)
      video_file = client.files.get(name=video_file.name)

    print(f'Video processing complete: {video_file.uri}')

    # You must use an explicit version suffix: "-flash-001", not just "-flash".
    model='models/gemini-2.0-flash-001'

    # Create a cache with a 5 minute TTL
    cache = client.caches.create(
        model=model,
        config=types.CreateCachedContentConfig(
          display_name='sherlock jr movie', # used to identify the cache
          system_instruction=(
              'You are an expert video analyzer, and your job is to answer '
              'the user\'s query based on the video file you have access to.'
          ),
          contents=[video_file],
          ttl="300s",
      )
    )

    # Construct a GenerativeModel which uses the created cache.
    response = client.models.generate_content(
      model = model,
      contents= (
        'Introduce different characters in the movie by describing '
        'their personality, looks, and names. Also list the timestamps '
        'they were introduced for the first time.'),
      config=types.GenerateContentConfig(cached_content=cache.name)
    )

    print(response.usage_metadata)

    # The output should look something like this:
    #
    # prompt_token_count: 696219
    # cached_content_token_count: 696190
    # candidates_token_count: 214
    # total_token_count: 696433

    print(response.text)

### PDFs

    from google import genai
    from google.genai import types
    import io
    import httpx

    client = genai.Client()

    long_context_pdf_path = "https://www.nasa.gov/wp-content/uploads/static/history/alsj/a17/A17_FlightPlan.pdf"

    # Retrieve and upload the PDF using the File API
    doc_io = io.BytesIO(httpx.get(long_context_pdf_path).content)

    document = client.files.upload(
      file=doc_io,
      config=dict(mime_type='application/pdf')
    )

    model_name = "gemini-2.0-flash-001"
    system_instruction = "You are an expert analyzing transcripts."

    # Create a cached content object
    cache = client.caches.create(
        model=model_name,
        config=types.CreateCachedContentConfig(
          system_instruction=system_instruction,
          contents=[document],
        )
    )

    # Display the cache details
    print(f'{cache=}')

    # Generate content using the cached prompt and document
    response = client.models.generate_content(
      model=model_name,
      contents="Please summarize this transcript",
      config=types.GenerateContentConfig(
        cached_content=cache.name
      ))

    # (Optional) Print usage metadata for insights into the API call
    print(f'{response.usage_metadata=}')

    # Print the generated text
    print('\n\n', response.text)

### List caches

It's not possible to retrieve or view cached content, but you can retrieve
cache metadata (`name`, `model`, `display_name`, `usage_metadata`,
`create_time`, `update_time`, and `expire_time`).

To list metadata for all uploaded caches, use `CachedContent.list()`:

    for cache in client.caches.list():
      print(cache)

To fetch the metadata for one cache object, if you know its name, use `get`:

    client.caches.get(name=name)

### Update a cache

You can set a new `ttl` or `expire_time` for a cache. Changing anything else
about the cache isn't supported.

The following example shows how to update the `ttl` of a cache using
`client.caches.update()`.

    from google import genai
    from google.genai import types

    client.caches.update(
      name = cache.name,
      config  = types.UpdateCachedContentConfig(
          ttl='300s'
      )
    )

To set the expiry time, it will accepts either a `datetime` object
or an ISO-formatted datetime string (`dt.isoformat()`, like
`2025-01-27T16:02:36.473528+00:00`). Your time must include a time zone
(`datetime.utcnow()` doesn't attach a time zone,
`datetime.now(datetime.timezone.utc)` does attach a time zone).

    from google import genai
    from google.genai import types
    import datetime

    # You must use a time zone-aware time.
    in10min = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)

    client.caches.update(
      name = cache.name,
      config  = types.UpdateCachedContentConfig(
          expire_time=in10min
      )
    )

### Delete a cache

The caching service provides a delete operation for manually removing content
from the cache. The following example shows how to delete a cache:

    client.caches.delete(cache.name)

### Explicit caching using the OpenAI library

If you're using an [OpenAI library](https://ai.google.dev/gemini-api/docs/openai), you can enable
explicit caching using the `cached_content` property on
[`extra_body`](https://ai.google.dev/gemini-api/docs/openai#extra-body).

## When to use explicit caching

Context caching is particularly well suited to scenarios where a substantial
initial context is referenced repeatedly by shorter requests. Consider using
context caching for use cases such as:

-   Chatbots with extensive [system instructions](https://ai.google.dev/gemini-api/docs/system-instructions)
-   Repetitive analysis of lengthy video files
-   Recurring queries against large document sets
-   Frequent code repository analysis or bug fixing

### How explicit caching reduces costs

Context caching is a paid feature designed to reduce overall operational costs.
Billing is based on the following factors:

1. **Cache token count:** The number of input tokens cached, billed at a reduced rate when included in subsequent prompts.
2. **Storage duration:** The amount of time cached tokens are stored (TTL), billed based on the TTL duration of cached token count. There are no minimum or maximum bounds on the TTL.
3. **Other factors:** Other charges apply, such as for non-cached input tokens and output tokens.

For up-to-date pricing details, refer to the Gemini API [pricing
page](https://ai.google.dev/pricing). To learn how to count tokens, see the [Token
guide](https://ai.google.dev/gemini-api/docs/tokens).

### Additional considerations

Keep the following considerations in mind when using context caching:

-   The _minimum_ input token count for context caching is 1,024 for 2.5 Flash and 2,048 for 2.5 Pro. The _maximum_ is the same as the maximum for the given model. (For more on counting tokens, see the [Token guide](https://ai.google.dev/gemini-api/docs/tokens)).
-   The model doesn't make any distinction between cached tokens and regular input tokens. Cached content is a prefix to the prompt.
-   There are no special rate or usage limits on context caching; the standard rate limits for `GenerateContent` apply, and token limits include cached tokens.
-   The number of cached tokens is returned in the `usage_metadata` from the create, get, and list operations of the cache service, and also in `GenerateContent` when using the cache.

---

# tokens.md

Python JavaScript Go

<br />

Gemini and other generative AI models process input and output at a granularity
called a _token_.

## About tokens

Tokens can be single characters like `z` or whole words like `cat`. Long words
are broken up into several tokens. The set of all tokens used by the model is
called the vocabulary, and the process of splitting text into tokens is called
_tokenization_.

For Gemini models, a token is equivalent to about 4 characters.
100 tokens is equal to about 60-80 English words.

When billing is enabled, the [cost of a call to the Gemini API](https://ai.google.dev/pricing) is
determined in part by the number of input and output tokens, so knowing how to
count tokens can be helpful.

## Try out counting tokens in a Colab

You can try out counting tokens by using a Colab.

|---------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [![](https://ai.google.dev/static/site-assets/images/docs/notebook-site-button.png)View on ai.google.dev](https://ai.google.dev/gemini-api/docs/tokens) | [![](https://www.tensorflow.org/images/colab_logo_32px.png)Try a Colab notebook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Counting_Tokens.ipynb) | [![](https://www.tensorflow.org/images/GitHub-Mark-32px.png)View notebook on GitHub](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Counting_Tokens.ipynb) |

## Context windows

The models available through the Gemini API have context windows that are
measured in tokens. The context window defines how much input you can provide
and how much output the model can generate. You can determine the size of the
context window by calling the [getModels endpoint](https://ai.google.dev/api/rest/v1/models/get) or
by looking in the [models documentation](https://ai.google.dev/gemini-api/docs/models/gemini).

In the following example, you can see that the `gemini-1.5-flash` model has an
input limit of about 1,000,000 tokens and an output limit of about 8,000 tokens,
which means a context window is 1,000,000 tokens.

<br />

    from google import genai

    client = genai.Client()
    model_info = client.models.get(model="gemini-2.0-flash")
    print(f"{model_info.input_token_limit=}")
    print(f"{model_info.output_token_limit=}")
    # ( e.g., input_token_limit=30720, output_token_limit=2048 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L25-L31

## Count tokens

All input to and output from the Gemini API is tokenized, including text, image
files, and other non-text modalities.

You can count tokens in the following ways:

### Count text tokens

    from google import genai

    client = genai.Client()
    prompt = "The quick brown fox jumps over the lazy dog."

    # Count tokens using the new client method.
    total_tokens = client.models.count_tokens(
        model="gemini-2.0-flash", contents=prompt
    )
    print("total_tokens: ", total_tokens)
    # ( e.g., total_tokens: 10 )

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )

    # The usage_metadata provides detailed token counts.
    print(response.usage_metadata)
    # ( e.g., prompt_token_count: 11, candidates_token_count: 73, total_token_count: 84 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L36-L54

### Count multi-turn (chat) tokens

    from google import genai
    from google.genai import types

    client = genai.Client()

    chat = client.chats.create(
        model="gemini-2.0-flash",
        history=[
            types.Content(
                role="user", parts=[types.Part(text="Hi my name is Bob")]
            ),
            types.Content(role="model", parts=[types.Part(text="Hi Bob!")]),
        ],
    )
    # Count tokens for the chat history.
    print(
        client.models.count_tokens(
            model="gemini-2.0-flash", contents=chat.get_history()
        )
    )
    # ( e.g., total_tokens: 10 )

    response = chat.send_message(
        message="In one sentence, explain how a computer works to a young child."
    )
    print(response.usage_metadata)
    # ( e.g., prompt_token_count: 25, candidates_token_count: 21, total_token_count: 46 )

    # You can count tokens for the combined history and a new message.
    extra = types.UserContent(
        parts=[
            types.Part(
                text="What is the meaning of life?",
            )
        ]
    )
    history = chat.get_history()
    history.append(extra)
    print(client.models.count_tokens(model="gemini-2.0-flash", contents=history))
    # ( e.g., total_tokens: 56 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L59-L98

### Count multimodal tokens

All input to the Gemini API is tokenized, including text, image files, and other
non-text modalities. Note the following high-level key points about tokenization
of multimodal input during processing by the Gemini API:

-   With Gemini 2.0, image inputs with both dimensions \<=384 pixels are counted as
    258 tokens. Images larger in one or both dimensions are cropped and scaled as
    needed into tiles of 768x768 pixels, each counted as 258 tokens. Prior to Gemini
    2.0, images used a fixed 258 tokens.

-   Video and audio files are converted to tokens at the following fixed rates:
    video at 263 tokens per second and audio at 32 tokens per second.

#### Image files

| **Note:** You'll get the same token count if you use a file uploaded using the File API or you provide the file as inline data.

Example that uses an uploaded image from the File API:

    from google import genai

    client = genai.Client()
    prompt = "Tell me about this image"
    your_image_file = client.files.upload(file=media / "organ.jpg")

    print(
        client.models.count_tokens(
            model="gemini-2.0-flash", contents=[prompt, your_image_file]
        )
    )
    # ( e.g., total_tokens: 263 )

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=[prompt, your_image_file]
    )
    print(response.usage_metadata)
    # ( e.g., prompt_token_count: 264, candidates_token_count: 80, total_token_count: 345 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L127-L144

Example that provides the image as inline data:

    from google import genai
    import PIL.Image

    client = genai.Client()
    prompt = "Tell me about this image"
    your_image_file = PIL.Image.open(media / "organ.jpg")

    # Count tokens for combined text and inline image.
    print(
        client.models.count_tokens(
            model="gemini-2.0-flash", contents=[prompt, your_image_file]
        )
    )
    # ( e.g., total_tokens: 263 )

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=[prompt, your_image_file]
    )
    print(response.usage_metadata)
    # ( e.g., prompt_token_count: 264, candidates_token_count: 80, total_token_count: 345 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L103-L122

#### Video or audio files

Audio and video are each converted to tokens at the following fixed rates:

-   Video: 263 tokens per second
-   Audio: 32 tokens per second

**Note:** You'll get the same token count if you use a file uploaded using the File API or you provide the file as inline data.

    from google import genai
    import time

    client = genai.Client()
    prompt = "Tell me about this video"
    your_file = client.files.upload(file=media / "Big_Buck_Bunny.mp4")

    # Poll until the video file is completely processed (state becomes ACTIVE).
    while not your_file.state or your_file.state.name != "ACTIVE":
        print("Processing video...")
        print("File state:", your_file.state)
        time.sleep(5)
        your_file = client.files.get(name=your_file.name)

    print(
        client.models.count_tokens(
            model="gemini-2.0-flash", contents=[prompt, your_file]
        )
    )
    # ( e.g., total_tokens: 300 )

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=[prompt, your_file]
    )
    print(response.usage_metadata)
    # ( e.g., prompt_token_count: 301, candidates_token_count: 60, total_token_count: 361 )
    https://github.com/google-gemini/api-examples/blob/9f5adb78a77820ef2d4f2a040d698481803e8214/python/count_tokens.py#L149-L174

### System instructions and tools

System instructions and tools also count towards the total token count for the
input.

If you use system instructions, the `total_tokens` count increases to
reflect the addition of `system_instruction`.

If you use function calling, the `total_tokens` count increases to reflect the
addition of `tools`.

---

# prompting-strategies.md

_Prompt design_ is the process of creating prompts, or natural language requests,
that elicit accurate, high quality responses from a language model.

This page introduces basic concepts, strategies, and best practices to get you
started designing prompts to get the most out of Gemini AI models.

## Topic-specific prompt guides

Looking for more specific prompt strategies? Check out our other prompting guides
on:

-   [Prompting with media files](https://ai.google.dev/gemini-api/docs/files#prompt-guide)
-   Prompting for image generation with [Imagen](https://ai.google.dev/gemini-api/docs/imagen#imagen-prompt-guide) and [Gemini Native Image Generation](https://ai.google.dev/gemini-api/docs/image-generation#prompt-guide)
-   [Prompting for video generation](https://ai.google.dev/gemini-api/docs/video#prompt-guide)

You can find other sample prompts in the [prompt gallery](https://ai.google.dev/gemini-api/prompts)
meant to interactively showcase many of the concepts shared in this guide.

## Clear and specific instructions

An effective and efficient way to customize model behavior is to provide it with
clear and specific instructions. Instructions can be in the form of a question,
step-by-step tasks, or as complex as mapping out a user's experience and mindset.

### Input

Input is the required text in the prompt that you want the model to provide a
response to. Inputs can be a question that the model
answers (question input), a task the model performs (task input), an entity the
model operates on (entity input), or partial input that the model completes or
continues (completion input).

| **Input type** | **Prompt**                                                                                                                                  | **Generated output**                                                                                                                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Question       | What's a good name for a flower shop that specializes in selling bouquets of dried flowers? Create a list of 5 options with just the names. | Here are 10 names for a flower shop specializing in dried flowers: 1. Everlasting Blooms 2. Dried & Delightful 3. The Petal Preserve 4. Whispers of Wildflowers 5. Forever Blooms                                                                                                            |
| Task           | `Give me a simple list of just the things that I must bring on a camping trip. The list should have 5 items.`                               | `1. **Tent:** Your shelter from the elements. 2. **Sleeping Bag:** Stay warm and comfortable. 3. **Sleeping Pad:** Insulation and cushioning for a good night's sleep. 4. **Headlamp or Flashlight:** Light for nighttime activities. 5. **First Aid Kit:** Be prepared for minor injuries.` |
| Entity         | Classify the following items as [large, small]: Elephant Mouse Snail                                                                        | Here's the classification: _ **Elephant:** Large _ **Mouse:** Small \* **Snail:** Small                                                                                                                                                                                                      |

#### Partial input completion

Generative language models work like an advanced auto completion tool. When you
provide partial content, the model can provide the rest of the content or what
it thinks is a continuation of that content as a response. When doing so, if you
include any examples or context, the model can take those examples or context
into account.

The following example provides a prompt with an instruction and an entity input:

|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `For the given order, return a JSON object that has the fields cheeseburger, hamburger, fries, or drink, with the value being the quantity. Order: A burger and a drink.` **Response:** `{ "cheeseburger": 0, "hamburger": 1, "fries": 0, "drink": 1 }` (gemini-2.5-flash) |

While the model did as prompted, writing out the instructions in natural language
can sometimes be challenging and it leaves a lot to the model's interpretation.
For example, a restaurants menu might contain many items. To reduce the size of
the JSON response, you probably want to omit the items that weren't ordered. In
this case, you can give an example and a [response prefix](https://ai.google.dev/gemini-api/docs/prompting-strategies#prefixes) and let
the model complete it:

|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** ` Valid fields are cheeseburger, hamburger, fries, and drink. Order: Give me a cheeseburger and fries Output: ``` { "cheeseburger": 1, "fries": 1 } ``` Order: I want two burgers, a drink, and fries. Output: ` **Response:** ` ``` { "hamburger": 2, "drink": 1, "fries": 1 } ``` ` (gemini-2.5-flash) |

Notice how "cheeseburger" was excluded from the output because it wasn't a part
of the order.

### Constraints

Specify any constraints on reading the prompt or generating a response. You can
tell the model what to do and not to do. For example, you can specify a constraint
in the prompt on how long you want a summary to be:

|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Summarize this text in one sentence: Text: A quantum computer exploits quantum mechanical phenomena to perform calculations exponentially faster than any modern traditional computer. At very tiny scales, physical matter acts as both particles and as waves, and quantum computing uses specialized hardware to leverage this behavior. The operating principles of quantum devices is beyond the scope of classical physics. When deployed at scale, quantum computers could be used in a wide variety of applications such as: in cybersecurity to break existing encryption methods while helping researchers create new ones, in meteorology to develop better weather forecasting etc. However, the current state of the art quantum computers are still largely experimental and impractical.` <br /> **Response:** `Exploiting quantum mechanical phenomena, quantum computers can perform calculations exponentially faster than traditional computers for potential applications like cybersecurity and meteorology, although they are currently largely experimental and impractical.` (gemini-2.5-flash) <br /> |

### Response format

You can give instructions that specify the format of the response. For example,
you can ask for the response to be formatted as a table, bulleted list, elevator
pitch, keywords, sentence, or paragraph. The following system instruction tells
the model to be more conversational in its response:

|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **System instruction** `All questions should be answered comprehensively with details, unless the user requests a concise response specifically.` **Prompt** `What is a smart way to make a business that sells DVD's in 2025?` **Response:** `Starting a business selling DVDs in 2025 presents significant challenges due to the overwhelming dominance of digital streaming and on-demand services; a "smart" approach would therefore require a highly specialized niche, a strong value proposition beyond just the disc, and likely a focus on community or collector markets rather than mainstream consumption. Here's a breakdown of what a smart DVD business in 2025 would likely entail: 1. Extreme Niche Specialization: You cannot compete with streaming libraries. Your business must focus on what digital doesn't offer easily or at all. This could include: * Out-of-Print & Rare Titles: Sourcing films or TV shows that have never been released digitally or are currently unavailable on major streaming platforms. ....` (gemini-2.5-flash) |

#### Format responses with the completion strategy

The [completion strategy](https://ai.google.dev/gemini-api/docs/prompting-strategies#completion) can also help format the response.
The following example prompts the model to create an essay outline:

|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Create an outline for an essay about hummingbirds.` **Response:** `Here is a possible outline for an essay about hummingbirds: I. Introduction A. Hook: Start with a captivating fact or description about hummingbirds (e.g., their speed, iridescent colors, or tiny size). B. Background: Briefly introduce hummingbirds �� where they are found (Americas), their reputation as unique birds. C. Thesis Statement: State the main point of the essay, which could be about the remarkable adaptations, behaviors, and ecological importance of hummingbirds. II. Appearance and Identification .....` (gemini-2.5-flash) |

The prompt didn't specify the format for the outline and the model chose a format
for you. To get the model to return an outline in a specific format, you can add
text that represents the start of the outline and let the model complete it based
on the pattern that you initiated.

|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Create an outline for an essay about hummingbirds. I. Introduction *` **Response:** `Okay, here is an outline for an essay about hummingbirds, starting from the introduction you provided: I. Introduction * Hook: Start with a captivating fact or description about hummingbirds (e.g., their speed, iridescent colors, or tiny size). * Background: Briefly introduce hummingbirds �� where they are found (Americas), their reputation as unique birds, and their general characteristics. * Thesis Statement: State the main point of the essay, focusing on the remarkable adaptations, behaviors, and ecological significance that make hummingbirds extraordinary. .....` (gemini-2.5-flash) |

## Zero-shot vs few-shot prompts

You can include examples in the prompt that show the model what getting it right
looks like. The model attempts to identify patterns and relationships from the
examples and applies them when generating a response. Prompts that contain a few
examples are called _few-shot_ prompts, while prompts that provide no
examples are called _zero-shot_ prompts. Few-shot prompts are often used
to regulate the formatting, phrasing, scoping, or general patterning of model
responses. Use specific and varied examples to help the model narrow its focus
and generate more accurate results.

We recommend to always include few-shot examples in your prompts. Prompts without
few-shot examples are likely to be less effective. In fact, you can remove
instructions from your prompt if your examples are clear enough in showing the
task at hand.

The following zero-shot prompt asks the model to choose the best explanation.

|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Please choose the best explanation to the question: Question: How is snow formed? Explanation1: Snow is formed when water vapor in the air freezes into ice crystals in the atmosphere, which can combine and grow into snowflakes as they fall through the atmosphere and accumulate on the ground. Explanation2: Water vapor freezes into ice crystals forming snow. Answer:` **Response:** `Explanation1 is the better explanation because it provides more detail on the process, including how ice crystals combine and grow into snowflakes as they fall through the atmosphere.` (gemini-2.5-flash) |

If your use case requires the model to produce concise responses, you can include
examples in the prompt that give preference to concise responses.

The following prompt provides two examples that show preference to the shorter
explanations. In the response, you can see that the examples guided the model to
choose the shorter explanation (`Explanation2`) as opposed to the longer
explanation (`Explanation1`) like it did previously.

|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Below are some examples showing a question, explanation, and answer format: Question: Why is the sky blue? Explanation1: The sky appears blue because of Rayleigh scattering, which causes shorter blue wavelengths of light to be scattered more easily than longer red wavelengths, making the sky look blue. Explanation2: Due to Rayleigh scattering effect. Answer: Explanation2 Question: What is the cause of earthquakes? Explanation1: Sudden release of energy in the Earth's crust. Explanation2: Earthquakes happen when tectonic plates suddenly slip or break apart, causing a release of energy that creates seismic waves that can shake the ground and cause damage. Answer: Explanation1 Now, Answer the following question given the example formats above: Question: How is snow formed? Explanation1: Snow is formed when water vapor in the air freezes into ice crystals in the atmosphere, which can combine and grow into snowflakes as they fall through the atmosphere and accumulate on the ground. Explanation2: Water vapor freezes into ice crystals forming snow. Answer:` **Response:** `Answer: Explanation2` (gemini-2.5-flash) |

### Optimal number of examples

Models like Gemini can often pick up on patterns using a few examples, though
you may need to experiment with the number of examples to provide in the prompt
for the best results. At the same time, if you include too many examples,
the model may start to [overfit](https://developers.google.com/machine-learning/glossary#overfitting)
the response to the examples.

### Patterns vs anti patterns

Using examples to show the model a pattern to follow is more effective than using
examples to show the model an anti pattern to avoid.

��� **Negative pattern:**

|--------------------------------------------------------------------------------------------------------------------------|
| **Example** `Don't end haikus with a question: Haiku are fun A short and simple poem Don't you enjoy them?` <br /> |

�� **Positive pattern:**

|----------------------------------------------------------------------------------------------------------------------|
| **Example** `Always end haikus with an assertion: Haiku are fun A short and simple poem A joy to write` <br /> |

### Consistent formatting

Make sure that the structure and formatting of few-shot examples are the same to
avoid responses with undesired formats. One of the primary objectives of adding
few-shot examples in prompts is to show the model the response format. Therefore,
it is essential to ensure a consistent format across all examples, especially
paying attention to XML tags, white spaces, newlines, and example splitters.

## Add context

You can include instructions and information in a prompt that the model needs
to solve a problem, instead of assuming that the model has all of the required
information. This contextual information helps the model understand the constraints
and details of what you're asking for it to do.

The following example asks the model to give troubleshooting guidance for a router:

|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `What should I do to fix my disconnected wifi? The light on my Google Wifi router is yellow and blinking slowly.` **Response:** `A yellow blinking light on your Google Wifi router usually indicates a problem with the internet connection. Here are some steps to troubleshoot and fix the issue: 1. Restart your router and modem: - Unplug your modem from the power outlet and wait for 30 seconds. - Plug your modem back in and wait for it to fully boot up. - Unplug your Google Wifi router and wait for 30 seconds. - Plug your Google Wifi router back in and wait for it to fully boot up. .....` (gemini-2.5-flash) |

The response looks like generic troubleshooting information that's not specific
to the router or the status of the LED indicator lights.

To customize the response for the specific router, you can add to the prompt the router's
troubleshooting guide as context for it to refer to when providing a response.

|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Answer the question using the text below. Respond with only the text provided. Question: What should I do to fix my disconnected wifi? The light on my Google Wifi router is yellow and blinking slowly. Text: Color: Slowly pulsing yellow What it means: There is a network error. What to do: Check that the Ethernet cable is connected to both your router and your modem and both devices are turned on. You might need to unplug and plug in each device again. Color: Fast blinking yellow What it means: You are holding down the reset button and are factory resetting this device. What to do: If you keep holding down the reset button, after about 12 seconds, the light will turn solid yellow. Once it is solid yellow, let go of the factory reset button. Color: Solid yellow What it means: Router is factory resetting. What to do: This can take up to 10 minutes. When it's done, the device will reset itself and start pulsing white, letting you know it's ready for setup. Color: Solid red What it means: Something is wrong. What to do: Critical failure. Factory reset the router. If the light stays red, contact Wifi customer support.` **Response:** `Check that the Ethernet cable is connected to both your router and your modem and both devices are turned on. You might need to unplug and plug in each device again.` (gemini-2.5-flash) |

## Add prefixes

A prefix is a word or phrase that you add to the prompt content that can serve
several purposes, depending on where you put the prefix:

-   **Input prefix:** Adding a prefix to the input signals semantically meaningful parts of the input to the model. For example, the prefixes "English:" and "French:" demarcate two different languages.
-   **Output prefix:** Even though the output is generated by the model, you can add a prefix for the output in the prompt. The output prefix gives the model information about what's expected as a response. For example, the output prefix "JSON:" signals to the model that the output should be in JSON format.
-   **Example prefix:** In few-shot prompts, adding prefixes to the examples provides labels that the model can use when generating the output, which makes it easier to parse output content.

In the following example, "Text:" is the input prefix and "The answer is:" is the
output prefix.

|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Prompt:** `Classify the text as one of the following categories. - large - small Text: Rhino The answer is: large Text: Mouse The answer is: small Text: Snail The answer is: small Text: Elephant The answer is:` **Response:** `The answer is: large` (gemini-2.5-flash) |

## Break down prompts into components

For use cases that require complex prompts, you can help the model manage this
complexity by breaking things down into simpler components.

1. **Break down instructions:** Instead of having many instructions in one
   prompt, create one prompt per instruction. You can choose which prompt to
   process based on the user's input.

2. **Chain prompts:** For complex tasks that involve multiple sequential steps,
   make each step a prompt and chain the prompts together in a sequence. In this
   sequential chain of prompts, the output of one prompt in the sequence becomes
   the input of the next prompt. The output of the last prompt in the sequence
   is the final output.

3. **Aggregate responses:** Aggregation is when you want to perform different
   parallel tasks on different portions of the data and aggregate the results to
   produce the final output. For example, you can tell the model to perform one
   operation on the first part of the data, perform another operation on the rest
   of the data and aggregate the results.

## Experiment with model parameters

Each call that you send to a model includes parameter values that control how
the model generates a response. The model can generate different results for
different parameter values. Experiment with different parameter values to get
the best values for the task. The parameters available for
different models may differ. The most common parameters are the following:

1. **Max output tokens:** Specifies the maximum number of tokens that can be
   generated in the response. A token is approximately four characters. 100
   tokens correspond to roughly 60-80 words.

2. **Temperature:** The temperature controls the degree of randomness in token
   selection. The temperature is used for sampling during response generation,
   which occurs when `topP` and `topK` are applied. Lower temperatures are good
   for prompts that require a more deterministic or less open-ended response,
   while higher temperatures can lead to more diverse or creative results. A
   temperature of 0 is deterministic, meaning that the highest probability
   response is always selected.

3. **`topK`:** The `topK` parameter changes how the model selects tokens for
   output. A `topK` of 1 means the selected token is the most probable among
   all the tokens in the model's vocabulary (also called greedy decoding),
   while a `topK` of 3 means that the next token is selected from among the 3
   most probable using the temperature. For each token selection step, the
   `topK` tokens with the highest probabilities are sampled. Tokens are then
   further filtered based on `topP` with the final token selected using
   temperature sampling.

4. **`topP`:** The `topP` parameter changes how the model selects tokens for
   output. Tokens are selected from the most to least probable until the sum of
   their probabilities equals the `topP` value. For example, if tokens A, B,
   and C have a probability of 0.3, 0.2, and 0.1 and the `topP` value is 0.5,
   then the model will select either A or B as the next token by using the
   temperature and exclude C as a candidate. The default `topP` value is 0.95.

5. **`stop_sequences`:** Set a stop sequence to
   tell the model to stop generating content. A stop sequence can be any
   sequence of characters. Try to avoid using a sequence of characters that
   may appear in the generated content.

## Prompt iteration strategies

Prompt design can sometimes require a few iterations before
you consistently get the response you're looking for. This section provides
guidance on some things you can try when iterating on your prompts:

1.  **Use different phrasing:** Using different words or phrasing in your prompts
    often yields different responses from the model even though they all mean the
    same thing. If you're not getting the expected results from your prompt, try
    rephrasing it.

    |----------------------------------------------------------------------------------------------------------------------------|
    | `Version 1: How do I bake a pie? Version 2: Suggest a recipe for a pie. Version 3: What's a good pie recipe?` <br /> |

2.  **Switch to an analogous task:** If you can't get the model to follow your
    instructions for a task, try giving it instructions for an analogous task
    that achieves the same result.

    This prompt tells the model to categorize a book by using predefined categories:

    |--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | **Prompt:** `Which category does The Odyssey belong to: thriller sci-fi mythology biography` **Response:** `The Odyssey belongs to the category of **mythology**. Here's why: * **Mythology:** The Odyssey tells the story of Odysseus, a hero from Greek mythology, and his journey home after the Trojan War. It features gods, monsters, and supernatural events common to Greek mythology. .....` (gemini-2.5-flash) |

    The response is correct, but the model didn't stay within the bounds of the
    options. You also want to model to just respond with one of the options instead
    of in a full sentence. In this case, you can rephrase the instructions as a
    multiple choice question and ask the model to choose an option.

    <br />

    |--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | **Prompt:** `Multiple choice problem: Which of the following options describes the book The Odyssey? Options: - thriller - sci-fi - mythology - biography` **Response:** `The correct answer is mythology.` (gemini-2.5-flash) |

3.  **Change the order of prompt content:** The order of the content in the prompt
    can sometimes affect the response. Try changing the content order and see
    how that affects the response.

        Version 1:
        [examples]
        [context]
        [input]

        Version 2:
        [input]
        [examples]
        [context]

        Version 3:
        [examples]
        [input]
        [context]

## Fallback responses

A fallback response is a response returned by the model when either the prompt
or the response triggers a safety filter. An example of a fallback response is
"I'm not able to help with that, as I'm only a language model."

If the model responds with a fallback response, try increasing the temperature.

## Things to avoid

-   Avoid relying on models to generate factual information.
-   Use with care on math and logic problems.

## Generative models under the hood

This section aims to answer the question - **_Is there randomness in generative
models' responses, or are they deterministic?_**

The short answer - yes to both. When you prompt a generative model, a text
response is generated in two stages. In the first stage, the generative model
processes the input prompt and generates a **probability distribution** over
possible tokens (words) that are likely to come next. For example, if you prompt
with the input text "The dog jumped over the ... ", the generative model will
produce an array of probable next words:

    [("fence", 0.77), ("ledge", 0.12), ("blanket", 0.03), ...]

This process is deterministic; a generative model will produce this same
distribution every time it's input the same prompt text.

In the second stage, the generative model converts these distributions into
actual text responses through one of several decoding strategies. A simple
decoding strategy might select the most likely token at every timestep. This
process would always be deterministic. However, you could instead choose to
generate a response by _randomly sampling_ over the distribution returned by the
model. This process would be stochastic (random). Control the degree of
randomness allowed in this decoding process by setting the temperature. A
temperature of 0 means only the most likely tokens are selected, and there's no
randomness. Conversely, a high temperature injects a high degree of randomness
into the tokens selected by the model, leading to more unexpected, surprising
model responses.

## Next steps

-   Now that you have a deeper understanding of prompt design, try writing your own prompts using [Google AI Studio](http://aistudio.google.com).
-   To learn about multimodal prompting, see [Prompting with media files](https://ai.google.dev/gemini-api/docs/files#prompt-guide).
-   To learn about image prompting, see the [Imagen prompt guide](https://ai.google.dev/gemini-api/docs/image-generation#imagen-prompt-guide)
-   To learn about video prompting, see the [Veo prompt guide](https://ai.google.dev/gemini-api/docs/video#prompt-guide)
