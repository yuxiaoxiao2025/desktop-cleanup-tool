调用大模型时，不同推理请求可能出现输入内容的重叠（例如多轮对话或对同一本书的多次提问）。上下文缓存（Context Cache）技术可以缓存这些请求的公共前缀，减少推理时的重复计算。这能提升响应速度，并在不影响回复效果的前提下降低您的使用成本。

为满足不同场景的需求，上下文缓存提供三种工作模式，可以根据对便捷性、确定性及成本的需求进行选择：

-   [显式缓存](#825f201c5fy6o)：需要**主动开启**的缓存模式。需要主动为指定内容创建缓存，以在有效期（5分钟）内实现确定性命中。除了输入 Token 计费，用于创建缓存的 Token 按输入 Token 标准单价的 125% 计费，后续命中仅需支付 10%的费用。
    
-   [隐式缓存](#2317ea09cfxok)：此为自动模式，无需额外配置，且无法关闭，适合追求便捷的通用场景。系统会**自动识别**请求内容的**公共前缀**并进行缓存，但缓存**命中率不确定**。对命中缓存的部分，按输入 Token 标准单价的 20% 计费。
    
-   [Session 缓存](#sc-section-title)：面向 Responses API 的多轮对话场景，在 header 中添加 `x-dashscope-session-cache: enable` ，服务端自动为上下文创建缓存。计费规则与显式缓存一致，用于创建缓存的 Token 按输入 Token 标准单价的 125% 计费，命中仅需支付 10%。
    

| **项目** | **显式缓存** | **隐式缓存** | **Session 缓存** |
| --- | --- | --- | --- |
| 是否影响回复效果 | 不影响 | 不影响 | 不影响 |
| 用于创建缓存Token计费 | 输入 Token 单价的125% | 输入 Token 单价的100% | 输入 Token 单价的125% |
| 命中缓存的输入 Token 计费 | 输入 Token 单价的10% | 输入 Token 单价的20% | 输入 Token 单价的10% |
| 缓存最少 Token 数 | 1024 | 256 | 1024 |
| 缓存有效期 | 5分钟（命中后重置） | 不确定，系统会定期清理长期未使用的缓存数据 | 5分钟（命中后重置） |

**说明**

-   使用 Chat Completions/DashScope API时，显式缓存、隐式缓存两者互斥，单个请求只能应用其中一种模式。
    
-   使用 Responses API时，未启用 Session 缓存 时，若模型支持将启用隐式缓存。
    

## **显式缓存**

与隐式缓存相比，显式缓存需要显式创建并承担相应开销，但能实现更高的缓存命中率和更低的访问延迟。

### **使用方式**

在 messages 中加入`"cache_control": {"type": "ephemeral"}`标记，系统将以每个`cache_control`标记位置为终点，向前回溯最多 20 个 `content` 块，尝试命中缓存。

> 单次请求最多支持加入4 个缓存标记。

-   **未命中缓存**
    
    系统将从messages数组开头到 `cache_control`标记之间的内容创建为新的缓存块，有效期为 5 分钟。
    
    > 缓存创建发生在模型响应之后，建议在创建请求完成后再尝试命中该缓存。
    
    > 缓存块的内容最少为 1024 Token。
    
-   **命中缓存**
    
    选取最长的匹配前缀作为命中的缓存块，并将该缓存块的有效期重置为5分钟。
    

以下示例说明其使用方式：

1.  **发起第一个请求**：发送包含超 1024 Token 文本 A 的系统消息，并加入缓存标记：
    
    ```
    [{"role": "system", "content": [{"type": "text", "text": A, "cache_control": {"type": "ephemeral"}}]}] 
    ```
    
    系统将创建首个缓存块，记为 A 缓存块。
    
2.  **发起第二个请求：**发送以下结构的请求：
    
    ```
    [
        {"role": "system", "content": A},
        <其他 message>
        {"role": "user","content": [{"type": "text", "text": B, "cache_control": {"type": "ephemeral"}}]}
    ]
    ```
    
    -   若“其他message”不超过 20 条，则命中 A 缓存块，并将其有效期重置为 5 分钟；同时，系统会基于 A、其他message和 B 创建一个新的缓存块。
        
    -   若“其他message”超过 20 条，则无法命中 A 缓存块，系统仍会基于完整上下文（A + 其他message + B）创建新缓存块。
        

### **支持的模型**

## 中国内地

[千问Max](https://help.aliyun.com/zh/model-studio/models#d4ccf72f23jh9)：qwen3-max

[千问Plus](https://help.aliyun.com/zh/model-studio/models#5ef284d4ed42p)：qwen3.5-plus、qwen-plus

[千问Flash](https://help.aliyun.com/zh/model-studio/models#13ff05e329blt)：qwen3.5-flash、qwen-flash

[千问Coder](https://help.aliyun.com/zh/model-studio/models#d698550551bob)：qwen3-coder-plus、qwen3-coder-flash

[千问VL](https://help.aliyun.com/zh/model-studio/models#3f1f1c8913fvo)：qwen3-vl-plus

[DeepSeek-阿里云](https://help.aliyun.com/zh/model-studio/deepseek-api)：deepseek-v3.2

## 全球

[千问Plus](https://help.aliyun.com/zh/model-studio/models#5ef284d4ed42p)：qwen3.5-plus

[千问Flash](https://help.aliyun.com/zh/model-studio/models#13ff05e329blt)：qwen3.5-flash

## 国际

[千问Max](https://help.aliyun.com/zh/model-studio/models#d4ccf72f23jh9)：qwen3-max

[千问Plus](https://help.aliyun.com/zh/model-studio/models#5ef284d4ed42p)：qwen3.5-plus、qwen-plus

[千问Flash](https://help.aliyun.com/zh/model-studio/models#13ff05e329blt)：qwen3.5-flash、qwen-flash

[千问Coder](https://help.aliyun.com/zh/model-studio/models#d698550551bob)：qwen3-coder-plus、qwen3-coder-flash

### **快速开始**

以下示例展示了在 OpenAI 兼容接口和 DashScope 协议中，缓存块的创建与命中机制。

## OpenAI 兼容

```
from openai import OpenAI
import os

client = OpenAI(
    # 若没有配置环境变量，请将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 模拟的代码仓库内容，最小可缓存提示词长度为 1024 Token
long_text_content = "<Your Code Here>" * 400

# 发起请求的函数
def get_completion(user_input):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": long_text_content,
                    # 在此处放置 cache_control 标记，将创建从 messages 数组的开头到当前 content 所在位置的所有内容作为缓存块。
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        # 每次的提问内容不同
        {
            "role": "user",
            "content": user_input,
        },
    ]
    completion = client.chat.completions.create(
        # 选择支持显式缓存的模型
        model="qwen3-coder-plus",
        messages=messages,
    )
    return completion

# 第一次请求
first_completion = get_completion("这段代码的内容是什么")
print(f"第一次请求创建缓存 Token：{first_completion.usage.prompt_tokens_details.cache_creation_input_tokens}")
print(f"第一次请求命中缓存 Token：{first_completion.usage.prompt_tokens_details.cached_tokens}")
print("=" * 20)
# 第二次请求，代码内容一致，只修改了提问问题
second_completion = get_completion("这段代码可以怎么优化")
print(f"第二次请求创建缓存 Token：{second_completion.usage.prompt_tokens_details.cache_creation_input_tokens}")
print(f"第二次请求命中缓存 Token：{second_completion.usage.prompt_tokens_details.cached_tokens}")
```

## DashScope

Python

```
import os
from dashscope import Generation
# 若使用新加坡地域的模型，请释放下列注释
# dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"

# 模拟的代码仓库内容，最小可缓存提示词长度为 1024 Token
long_text_content = "<Your Code Here>" * 400

# 发起请求的函数
def get_completion(user_input):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": long_text_content,
                    # 在此处放置 cache_control 标记，将创建从 messages 数组的开头到当前 content 所在位置的所有内容作为缓存块。
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        # 每次的提问内容不同
        {
            "role": "user",
            "content": user_input,
        },
    ]
    response = Generation.call(
        # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key = "sk-xxx",
        api_key=os.getenv("DASHSCOPE_API_KEY"), 
        model="qwen3-coder-plus",
        messages=messages,
        result_format="message"
    )
    return response

# 第一次请求
first_completion = get_completion("这段代码的内容是什么")
print(f"第一次请求创建缓存 Token：{first_completion.usage.prompt_tokens_details['cache_creation_input_tokens']}")
print(f"第一次请求命中缓存 Token：{first_completion.usage.prompt_tokens_details['cached_tokens']}")
print("=" * 20)
# 第二次请求，代码内容一致，只修改了提问问题
second_completion = get_completion("这段代码可以怎么优化")
print(f"第二次请求创建缓存 Token：{second_completion.usage.prompt_tokens_details['cache_creation_input_tokens']}")
print(f"第二次请求命中缓存 Token：{second_completion.usage.prompt_tokens_details['cached_tokens']}")
```

Java

```
// Java SDK 最低版本为 2.21.6
import com.alibaba.dashscope.aigc.generation.Generation;
import com.alibaba.dashscope.aigc.generation.GenerationParam;
import com.alibaba.dashscope.aigc.generation.GenerationResult;
import com.alibaba.dashscope.common.Message;
import com.alibaba.dashscope.common.MessageContentText;
import com.alibaba.dashscope.common.Role;
import com.alibaba.dashscope.exception.ApiException;
import com.alibaba.dashscope.exception.InputRequiredException;
import com.alibaba.dashscope.exception.NoApiKeyException;

import java.util.Arrays;
import java.util.Collections;

public class Main {
    private static final String MODEL = "qwen3-coder-plus";
    // 模拟代码仓库内容（400次重复确保超过1024 Token）
    private static final String LONG_TEXT_CONTENT = generateLongText(400);
    private static String generateLongText(int repeatCount) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < repeatCount; i++) {
            sb.append("<Your Code Here>");
        }
        return sb.toString();
    }
    private static GenerationResult getCompletion(String userQuestion)
            throws NoApiKeyException, ApiException, InputRequiredException {
        // 若使用新加坡地域模型，请将 https://dashscope.aliyuncs.com/api/v1 修改为 https://dashscope-intl.aliyuncs.com/api/v1
        Generation gen = new Generation("http", "https://dashscope.aliyuncs.com/api/v1");

        // 构建带缓存控制的系统消息
        MessageContentText systemContent = MessageContentText.builder()
                .type("text")
                .text(LONG_TEXT_CONTENT)
                .cacheControl(MessageContentText.CacheControl.builder()
                        .type("ephemeral") // 设置缓存类型
                        .build())
                .build();

        Message systemMsg = Message.builder()
                .role(Role.SYSTEM.getValue())
                .contents(Collections.singletonList(systemContent))
                .build();
        Message userMsg = Message.builder()
                .role(Role.USER.getValue())
                .content(userQuestion)
                .build();

        // 构建请求参数
        GenerationParam param = GenerationParam.builder()
                .model(MODEL)
                .messages(Arrays.asList(systemMsg, userMsg))
                .resultFormat(GenerationParam.ResultFormat.MESSAGE)
                .build();
        return gen.call(param);
    }

    private static void printCacheInfo(GenerationResult result, String requestLabel) {
        System.out.printf("%s创建缓存 Token: %d%n", requestLabel, result.getUsage().getPromptTokensDetails().getCacheCreationInputTokens());
        System.out.printf("%s命中缓存 Token: %d%n", requestLabel, result.getUsage().getPromptTokensDetails().getCachedTokens());
    }

    public static void main(String[] args) {
        try {
            // 第一次请求
            GenerationResult firstResult = getCompletion("这段代码的内容是什么");
            printCacheInfo(firstResult, "第一次请求");
            System.out.println(new String(new char[20]).replace('\0', '='));            // 第二次请求
            GenerationResult secondResult = getCompletion("这段代码可以怎么优化");
            printCacheInfo(secondResult, "第二次请求");
        } catch (NoApiKeyException | ApiException | InputRequiredException e) {
            System.err.println("API调用失败: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
```

模拟的代码仓库内容通过添加 `cache_control`标记启用显式缓存。后续针对该代码仓库的提问请求，系统可复用该缓存块，无需重新计算，可获得比创建缓存前更快的响应与更低的成本。

```
第一次请求创建缓存 Token：1605
第一次请求命中缓存 Token：0
====================
第二次请求创建缓存 Token：0
第二次请求命中缓存 Token：1605
```

### 使用多个缓存标记实现精细控制

在复杂场景中，提示词通常由多个重用频率不同的部分组成。使用多个缓存标记可实现精细控制。

例如，智能客服的提示词通常包括：

-   **系统人设：**高度稳定，几乎不变。
    
-   **外部知识：**半稳定，通过知识库检索或工具查询获得，可能在连续对话中保持不变。
    
-   **对话历史：**动态增长。
    
-   **当前问题：**每次不同。
    

如果将整个提示词作为一个整体缓存，任何微小变化（如外部知识改变）都可能导致无法命中缓存。

在请求中最多可设置四个缓存标记，为提示词的不同部分分别创建缓存块，从而提升命中率并实现精细控制。

### **如何计费**

显式缓存仅影响输入 Token 的计费方式。规则如下：

-   **创建缓存**：新创建的缓存内容按标准输入单价的 125% 计费。若新请求的缓存内容包含已有缓存作为前缀，则仅对新增部分计费（即新缓存 Token 数减去已有缓存 Token 数）。
    
    例如：若已有 1200 Token 的缓存 A，新请求需缓存 1500 Token 的内容 AB，则前 1200 Token 按缓存命中计费（标准单价的 10%），新增的 300 Token 按创建缓存计费（标准单价的 125%）。
    
    > 创建缓存所用的 Token数通过`cache_creation_input_tokens` 参数查看。
    
-   **命中缓存**：按标准输入单价的 10% 计费。
    
    > 命中缓存的 Token数通过 `cached_tokens` 参数查看。
    
-   **其他 Token**：未命中且未创建缓存的 Token 按原价计费。
    

### **可缓存内容**

仅 `messages` 数组中的以下消息类型支持添加缓存标记：

-   系统消息（System Message）
    
-   用户消息（User Message）
    
    > 使用`qwen3-vl-plus`模型创建缓存时，`cache_control`标记可放置在多模态内容或文本之后，其位置不影响缓存整个用户消息的效果。
    
-   助手消息（Assistant Message）
    
-   工具消息（Tool Message，即工具执行后的结果）
    
    > 若请求包含 `tools` 参数，在`messages`中添加缓存标记还会缓存其中的工具描述信息。
    

以系统消息为例，需将 `content` 字段改为数组形式，并添加 `cache_control` 字段：

```
{
  "role": "system",
  "content": [
    {
      "type": "text",
      "text": "<指定的提示词>",
      "cache_control": {
        "type": "ephemeral"
      }
    }
  ]
}
```

此结构同样适用于 `messages` 数组中的其他消息类型。

### **缓存限制**

-   最小可缓存提示词长度为 **1024** Token。
    
-   缓存采用从后向前的前缀匹配策略，系统会自动检查最近的 20 个 content 块。若待匹配内容与带有 `cache_control` 标记的消息之间间隔超过 20 个 content 块，则无法命中缓存。
    
-   仅支持将 `type` 设置为 `ephemeral`，有效期为 5 分钟。
    
-   单次请求最多可添加 4 个缓存标记。
    
    > 若缓存标记个数大于4，则最后四个缓存标记生效。
    

### **使用示例**

**针对长文本的不同提问**

```
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 以下为中国内地（北京）base_url，国际（新加坡）base_url为https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 模拟的代码仓库内容
long_text_content = "<Your Code Here>" * 400

# 发起请求的函数
def get_completion(user_input):
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": long_text_content,
                    # 在此处放置 cache_control 标记，将创建从messages数组开始，到本content结束位置（即模拟的代码仓库内容）的缓存。
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        },
        {
            "role": "user",
            "content": user_input,
        },
    ]
    completion = client.chat.completions.create(
        # 选择支持显式缓存的模型
        model="qwen3-coder-plus",
        messages=messages,
    )
    return completion

# 第一次请求
first_completion = get_completion("这段代码的内容是什么")
created_cache_tokens = first_completion.usage.prompt_tokens_details.cache_creation_input_tokens
print(f"第一次请求创建缓存 Token：{created_cache_tokens}")
hit_cached_tokens = first_completion.usage.prompt_tokens_details.cached_tokens
print(f"第一次请求命中缓存 Token：{hit_cached_tokens}")
print(f"第一次请求未命中也未创建缓存的 Token：{first_completion.usage.prompt_tokens-created_cache_tokens-hit_cached_tokens}")
print("=" * 20)
# 第二次请求，代码内容一致，只修改了提问问题
second_completion = get_completion("这段代码有哪些可以优化的地方")
created_cache_tokens = second_completion.usage.prompt_tokens_details.cache_creation_input_tokens
print(f"第二次请求创建缓存 Token：{created_cache_tokens}")
hit_cached_tokens = second_completion.usage.prompt_tokens_details.cached_tokens
print(f"第二次请求命中缓存 Token：{hit_cached_tokens}")
print(f"第二次请求未命中也未创建缓存的 Token：{second_completion.usage.prompt_tokens-created_cache_tokens-hit_cached_tokens}")
```

此示例缓存代码仓库内容作为前缀。后续针对该仓库进行不同提问。

```
第一次请求创建缓存 Token：1605
第一次请求命中缓存 Token：0
第一次请求未命中也未创建缓存的 Token：13
====================
第二次请求创建缓存 Token：0
第二次请求命中缓存 Token：1605
第二次请求未命中也未创建缓存的 Token：15
```

> 系统为保证模型效果，会追加少量内部Token，这部分Token按标准输入价格计费，请参见[常见问题](#b728b718d5dxf)。

**持续多轮对话**

在日常聊天的多轮对话场景，可将每一次请求的 messages 数组中最后一个 content 添加缓存标记。从第二轮对话开始，每次请求都将命中并刷新前一轮对话创建的缓存块，且创建新的缓存块。

```
from openai import OpenAI
import os
  
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 以下为中国内地（北京）base_url，国际（新加坡）base_url为https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

system_prompt = "你是说话风趣的人。" * 400
messages = [{"role": "system", "content": system_prompt}]

def get_completion(messages):
    completion = client.chat.completions.create(
        model="qwen3-coder-plus",
        messages=messages,
    )
    return completion

while True:
    user_input = input("请输入：")
    messages.append({"role": "user", "content": [{"type": "text", "text": user_input, "cache_control": {"type": "ephemeral"}}]})
    completion = get_completion(messages)
    print(f"[AI Response] {completion.choices[0].message.content}")
    messages.append(completion.choices[0].message)
    created_cache_tokens = completion.usage.prompt_tokens_details.cache_creation_input_tokens
    hit_cached_tokens = completion.usage.prompt_tokens_details.cached_tokens
    uncached_tokens = completion.usage.prompt_tokens - created_cache_tokens - hit_cached_tokens
    print(f"[Cache Info] 创建缓存 Token：{created_cache_tokens}")
    print(f"[Cache Info] 命中缓存 Token：{hit_cached_tokens}")
    print(f"[Cache Info] 未命中也未创建缓存的 Token：{uncached_tokens}")
```

运行以上代码，输入问题与大模型沟通，每次提问都会命中前一轮创建的缓存块。

## **隐式缓存**

### **支持的模型**

## 中国内地

在[中国内地部署模式](https://help.aliyun.com/zh/model-studio/regions/#080da663a75xh)下，接入点与数据存储均位于**北京地域**，模型推理计算资源仅限于中国内地。

-   **文本生成模型**
    
    -   [千问 Max](https://help.aliyun.com/zh/model-studio/models#cfc131abafghw)：qwen3-max、qwen-max
        
    -   [千问 Plus](https://help.aliyun.com/zh/model-studio/models#6c45e49509gtr)：qwen-plus
        
    -   [千问 Flash](https://help.aliyun.com/zh/model-studio/models#d617df95f1g9h)：qwen-flash
        
    -   [千问 Turbo](https://help.aliyun.com/zh/model-studio/models#8708390fdb66x)：qwen-turbo
        
    -   [千问 Coder](https://help.aliyun.com/zh/model-studio/models#d698550551bob)：qwen3-coder-plus、qwen3-coder-flash
        
    -   [DeepSeek](https://help.aliyun.com/zh/model-studio/models#935bd5ba5cg5d)：deepseek-v3.2、deepseek-v3.1、deepseek-v3、deepseek-r1
        
    -   [Kimi](https://help.aliyun.com/zh/model-studio/models#0ca6cec0252yp)：kimi-k2.5、kimi-k2-thinking、Moonshot-Kimi-K2-Instruct
        
    -   [GLM](https://help.aliyun.com/zh/model-studio/models#glm4.5)：glm-5、glm-4.7、glm-4.6
        
    -   [MiniMax](https://help.aliyun.com/zh/model-studio/models#6194236b53fx0)：MiniMax-M2.5、MiniMax-M2.1
        
-   **视觉理解模型**
    
    -   [千问 VL](https://help.aliyun.com/zh/model-studio/models#3f1f1c8913fvo)：qwen3-vl-plus、qwen3-vl-flash、qwen-vl-max、qwen-vl-plus
        
-   **行业模型**
    
    -   [角色扮演](https://help.aliyun.com/zh/model-studio/models#083f31bde1lv3)：qwen-plus-character
        
    -   [数据挖掘](https://help.aliyun.com/zh/model-studio/data-mining-qwen-doc)：qwen-doc-turbo
        

## 全球

在[全球部署模式](https://help.aliyun.com/zh/model-studio/regions/#080da663a75xh)下，接入点与数据存储均位于**美国（弗吉尼亚）地域**，模型推理计算资源在全球范围内动态调度。

-   **文本生成模型**
    
    -   [千问 Max](https://help.aliyun.com/zh/model-studio/models#cfc131abafghw)：qwen3-max
        
    -   [千问 Plus](https://help.aliyun.com/zh/model-studio/models#6c45e49509gtr)：qwen-plus
        
    -   [千问 Flash](https://help.aliyun.com/zh/model-studio/models#d617df95f1g9h)：qwen-flash
        
    -   [千问 Coder](https://help.aliyun.com/zh/model-studio/models#d698550551bob)：qwen3-coder-plus、qwen3-coder-flash
        
-   **视觉理解模型**
    
    -   [千问 VL](https://help.aliyun.com/zh/model-studio/models#3f1f1c8913fvo)：qwen3-vl-plus、qwen3-vl-flash
        

## 国际

在[国际部署模式](https://help.aliyun.com/zh/model-studio/regions/#080da663a75xh)下，接入点与数据存储均位于**新加坡地域**，模型推理计算资源在全球范围内动态调度（不含中国内地）。

-   **文本生成模型**
    
    -   [千问 Max](https://help.aliyun.com/zh/model-studio/models#c2d5833ae4jmo)：qwen3-max、qwen-max
        
    -   [千问 Plus](https://help.aliyun.com/zh/model-studio/models#6ad3cd90f0c5r)：qwen-plus
        
    -   [千问 Flash](https://help.aliyun.com/zh/model-studio/models#59857de48eps5)：qwen-flash
        
    -   [千问 Turbo](https://help.aliyun.com/zh/model-studio/models#ede6678dedqbz)：qwen-turbo
        
    -   [千问 Coder](https://help.aliyun.com/zh/model-studio/models#4f6fa69743l4j)：qwen3-coder-plus、qwen3-coder-flash
        
-   **视觉理解模型**
    
    -   [千问 VL](https://help.aliyun.com/zh/model-studio/models#3f1f1c8913fvo)：qwen3-vl-plus、qwen3-vl-flash、qwen-vl-max、qwen-vl-plus
        
-   **行业模型**
    
    -   [角色扮演](https://help.aliyun.com/zh/model-studio/models#083f31bde1lv3)：qwen-plus-character-ja
        

## 美国

在[美国部署模式](https://help.aliyun.com/zh/model-studio/regions/#080da663a75xh)下，接入点与数据存储均位于**美国（弗吉尼亚）地域**，模型推理计算资源仅限于美国境内。

-   **文本生成模型**
    
    -   [千问 Plus](https://help.aliyun.com/zh/model-studio/models#6c45e49509gtr)：qwen-plus-us
        
    -   [千问 Flash](https://help.aliyun.com/zh/model-studio/models#d617df95f1g9h)：qwen-flash-us
        
-   **视觉理解模型**
    
    -   [千问 VL](https://help.aliyun.com/zh/model-studio/models#3f1f1c8913fvo)：qwen3-vl-flash-us
        

**说明**

暂不支持快照与 latest 模型。

### **工作方式**

向支持隐式缓存的模型发送请求时，该功能会自动开启。系统的工作方式如下：

1.  **查找**：收到请求后，系统基于**前缀匹配**原则，检查缓存中是否存在请求中 `messages` 数组内容的公共前缀。
    
2.  **判断**：
    
    -   若命中缓存，系统直接使用缓存结果进行后续部分的推理。
        
    -   若未命中，系统按常规处理请求，并将本次提示词的前缀存入缓存，以备后续请求使用。
        

> 系统会定期清理长期未使用的缓存数据。上下文缓存命中概率并非100%，即使请求上下文完全一致，仍可能未命中，具体命中概率由系统判定。

**说明**

不足 256 Token 的内容不会被缓存。

### **提升命中缓存的概率**

隐式缓存的命中逻辑是判断不同请求的**前缀**是否存在重复内容。为提高命中概率，**请将重复内容置于提示词开头，差异内容置于末尾。**

-   **文本模型**：假设系统已缓存"ABCD"，则请求"ABE"可能命中"AB"部分，而请求"BCD"则无法命中。
    
-   **视觉理解模型：**
    
    -   对**同一图像或视频**进行多次提问：将图像或视频放在文本信息前会提高命中概率。
        
    -   对**不同图像或视频**提问同一问题：将文本信息放在图像或视频前面会提高命中概率。
        

### 如何计费

开启隐式缓存模式无需额外付费。

当请求命中缓存时，命中的输入 Token 按 `cached_token` 计费（单价为`input_token`单价的**20%**）；未被命中的输入 Token 按标准 `input_token`计费。输出 Token 仍按原价计费。

示例：某请求包含 10,000 个输入 Token，其中 5,000 个命中缓存。费用计算如下：

-   未命中 Token (5,000)：按 100% 单价计费
    
-   命中 Token (5,000)：按 20% 单价计费
    

总输入费用相当于无缓存模式的 60%：(50% × 100%) + (50% × 20%) = 60%。

![image.png](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/1913916571/p893561.png)

可从[返回结果](#366ab5759d8ab)的`cached_tokens`属性获取命中缓存的 Token 数。

> [OpenAI兼容-Batch（文件输入）](https://help.aliyun.com/zh/model-studio/batch-interfaces-compatible-with-openai/)方式调用无法享受缓存折扣。

### **命中缓存的案例**

## 文本生成模型

## OpenAI兼容

当您使用 OpenAI 兼容的方式调用模型并触发了隐式缓存后，可以得到如下的返回结果，在`usage.prompt_tokens_details.cached_tokens`可以查看命中缓存的 Token 数（该数值为`usage.prompt_tokens`的一部分）。

```
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "我是阿里云开发的一款超大规模语言模型，我叫千问。"
            },
            "finish_reason": "stop",
            "index": 0,
            "logprobs": null
        }
    ],
    "object": "chat.completion",
    "usage": {
        "prompt_tokens": 3019,
        "completion_tokens": 104,
        "total_tokens": 3123,
        "prompt_tokens_details": {
            "cached_tokens": 2048
        }
    },
    "created": 1735120033,
    "system_fingerprint": null,
    "model": "qwen-plus",
    "id": "chatcmpl-6ada9ed2-7f33-9de2-8bb0-78bd4035025a"
}
```

## DashScope

当您使用DashScope Python SDK 或 HTTP 方式调用模型并触发了隐式缓存后，可以得到如下的返回结果，在`usage.prompt_tokens_details.cached_tokens`可以查看命中缓存的 Token 数（该数值是 `usage.input_tokens` 的一部分。）。

```
{
    "status_code": 200,
    "request_id": "f3acaa33-e248-97bb-96d5-cbeed34699e1",
    "code": "",
    "message": "",
    "output": {
        "text": null,
        "finish_reason": null,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "我是一个来自阿里云的大规模语言模型，我叫千问。我可以生成各种类型的文本，如文章、故事、诗歌、故事等，并能够根据不同的场景和需求进行变换和扩展。此外，我还能够回答各种问题，提供帮助和解决方案。如果您有任何问题或需要帮助，请随时告诉我，我会尽力提供支持。请注意，连续重复相同的内容可能无法获得更详细的答复，建议您提供更多具体信息或变化提问方式以便我更好地理解您的需求。"
                }
            }
        ]
    },
    "usage": {
        "input_tokens": 3019,
        "output_tokens": 101,
        "prompt_tokens_details": {
            "cached_tokens": 2048
        },
        "total_tokens": 3120
    }
}
```

## 视觉理解模型

## OpenAI兼容

当您使用 OpenAI 兼容的方式调用模型并触发了隐式缓存后，可以得到如下的返回结果，在`usage.prompt_tokens_details.cached_tokens`可以查看命中缓存的 Token 数（该 Token 数是`usage.prompt_tokens`的一部分）。

> qwen3-vl-plus、qwen3-vl-flash模型使用 OpenAI  SDK 调用支持隐式缓存功能，但暂时无法查看`cached_tokens`。

```
{
  "id": "chatcmpl-3f3bf7d0-b168-9637-a245-dd0f946c700f",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": "这张图像展示了一位女性和一只狗在海滩上互动的温馨场景。女性穿着格子衬衫，坐在沙滩上，面带微笑地与狗进行互动。狗是一只大型的浅色犬种，戴着彩色的项圈，前爪抬起，似乎在与女性握手或击掌。背景是广阔的海洋和天空，阳光从画面的右侧照射过来，给整个场景增添了一种温暖而宁静的氛围。",
        "refusal": null,
        "role": "assistant",
        "audio": null,
        "function_call": null,
        "tool_calls": null
      }
    }
  ],
  "created": 1744956927,
  "model": "qwen-vl-max",
  "object": "chat.completion",
  "service_tier": null,
  "system_fingerprint": null,
  "usage": {
    "completion_tokens": 93,
    "prompt_tokens": 1316,
    "total_tokens": 1409,
    "completion_tokens_details": null,
    "prompt_tokens_details": {
      "audio_tokens": null,
      "cached_tokens": 1152
    }
  }
}
```

## DashScope

当您使用DashScope Python SDK 或 HTTP 方式调用模型并触发了隐式缓存后，命中缓存的Token数包含在总输入Token（usage.input\_tokens）中，具体查看位置因地域和模型而异：

-   北京地域：
    
    -   `qwen-vl-max`、`qwen-vl-plus`：在`usage.prompt_tokens_details.cached_tokens`查看 
        
    -   `qwen3-vl-plus`、`qwen3-vl-flash`：在 `usage.cached_tokens`查看 
        
-   新加坡地域：所有模型均查看 `usage.cached_tokens`
    

> 目前使用`usage.cached_tokens`的模型，后续将升级至`usage.prompt_tokens_details.cached_tokens`。

```
{
  "status_code": 200,
  "request_id": "06a8f3bb-d871-9db4-857d-2c6eeac819bc",
  "code": "",
  "message": "",
  "output": {
    "text": null,
    "finish_reason": null,
    "choices": [
      {
        "finish_reason": "stop",
        "message": {
          "role": "assistant",
          "content": [
            {
              "text": "这张图像展示了一位女性和一只狗在海滩上互动的温馨场景。女性穿着格子衬衫，坐在沙滩上，面带微笑地与狗进行互动。狗是一只大型犬，戴着彩色项圈，前爪抬起，似乎在与女性握手或击掌。背景是广阔的海洋和天空，阳光从画面右侧照射过来，给整个场景增添了一种温暖而宁静的氛围。"
            }
          ]
        }
      }
    ]
  },
  "usage": {
    "input_tokens": 1292,
    "output_tokens": 87,
    "input_tokens_details": {
      "text_tokens": 43,
      "image_tokens": 1249
    },
    "total_tokens": 1379,
    "output_tokens_details": {
      "text_tokens": 87
    },
    "image_tokens": 1249,
    "prompt_tokens_details": {
      "cached_tokens": 1152
    }
  }
}
```

### **典型场景**

如果您的不同请求有着相同的前缀信息，上下文缓存可以有效提升这些请求的推理速度，降低推理成本与首包延迟。以下是几个典型的应用场景：

1.  **基于长文本的问答**
    
    适用于需要针对固定的长文本（如小说、教材、法律文件等）发送多次请求的业务场景。
    
    **第一次请求的消息数组**
    
    ```
    messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
              {"role": "user","content": "<文章内容> 这篇课文表达了作者怎样的思想感情？"}]
    ```
    
    **之后请求的消息数组**
    
    ```
    messages = [{"role": "system","content": "你是一个语文老师，你可以帮助学生进行阅读理解。"},
              {"role": "user","content": "<文章内容> 请赏析这篇课文的第三自然段。"}]
    ```
    
    虽然提问的问题不同，但都基于同一篇文章。相同的系统提示和文章内容构成了大量重复的前缀信息，有较大概率命中缓存。
    
2.  **代码自动补全**
    
    在代码自动补全场景，大模型会结合上下文中存在的代码进行代码自动补全。随着用户的持续编码，代码的前缀部分会保持不变。上下文缓存可以缓存之前的代码，提升补全速度。
    
3.  **多轮对话**
    
    实现多轮对话需要将每一轮的对话信息添加到 messages 数组中，因此每轮对话的请求都会存在与前轮对话前缀相同的情况，有较高概率命中缓存。
    
    **第一轮对话的消息数组**
    
    ```
    messages=[{"role": "system","content": "You are a helpful assistant."},
              {"role": "user","content": "你是谁？"}]
    ```
    
    **第二轮对话的消息数组**
    
    ```
    messages=[{"role": "system","content": "You are a helpful assistant."},
              {"role": "user","content": "你是谁？"},
              {"role": "assistant","content": "我是由阿里云开发的千问。"},
              {"role": "user","content": "你能干什么？"}]
    ```
    
    随着对话轮数的增加，缓存带来的推理速度优势与成本优势会更明显。
    
4.  **角色扮演或 Few Shot**
    
    在角色扮演或 Few-shot 学习的场景中，您通常需要在提示词中加入大量信息来指引大模型的输出格式，这样不同的请求之间会有大量重复的前缀信息。
    
    以让大模型扮演营销专家为例，System prompt包含有大量文本信息，以下是两次请求的消息示例：
    
    ```
    system_prompt = """你是一位经验丰富的营销专家。请针对不同产品提供详细的营销建议，格式如下：
    
    1. 目标受众：xxx
    
    2. 主要卖点：xxx
    
    3. 营销渠道：xxx
    ...
    12. 长期发展策略：xxx
    
    请确保你的建议具体、可操作，并与产品特性高度相关。"""
    
    # 第一次请求的user message 提问关于智能手表
    messages_1=[
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": "请为一款新上市的智能手表提供营销建议。"}
    ]
    
    # 第二次请求的user message 提问关于笔记本电脑，由于system_prompt相同，有较大概率命中 Cache
    messages_2=[
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": "请为一款新上市的笔记本电脑提供营销建议。"}
    ]
    ```
    
    使用上下文缓存后，即使用户频繁更换询问的产品类型（如从智能手表到笔记本电脑），系统也可以在触发缓存后快速响应。
    
5.  **视频理解**
    
    在视频理解场景中，如果对同一个视频提问多次，将`video`放在`text`前会提高命中缓存的概率；如果对不同的视频提问相同的问题，则将`text`放在`video`前面，会提高命中缓存的概率。以下是对同一个视频请求两次的消息示例：
    
    ```
    # 第一次请求的user message 提问这段视频的内容
    messages1 = [
        {"role":"system","content":[{"text": "You are a helpful assistant."}]},
        {"role": "user",
            "content": [
                {"video": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250328/eepdcq/phase_change_480p.mov"},
                {"text": "这段视频的内容是什么?"}
            ]
        }
    ]
    
    # 第二次请求的user message 提问关于视频时间戳相关的问题，由于基于同一个视频进行提问，将video放在text前面，有较大概率命中 Cache
    messages2 = [
        {"role":"system","content":[{"text": "You are a helpful assistant."}]},
        {"role": "user",
            "content": [
                {"video": "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250328/eepdcq/phase_change_480p.mov"},
                {"text": "请你描述下视频中的一系列活动事件，以JSON格式输出开始时间（start_time）、结束时间（end_time）、事件（event），不要输出```json```代码段"}
            ]
        }
    ]
    ```
    

## **Session 缓存**

### **概述**

Session 缓存 是面向 Responses API 多轮对话场景的缓存模式。与显式缓存需要手动添加 `cache_control` 标记不同，Session 缓存 由服务端自动处理缓存逻辑，只需通过 HTTP header 控制开关，按正常多轮对话方式调用即可。

> 在使用 `previous_response_id` 进行多轮对话时，开启 Session 缓存 后，服务端会自动缓存对话上下文，降低推理延迟与使用成本。

### **使用方式**

在请求 header 中添加以下字段即可控制 Session 缓存 的开关：

-   `x-dashscope-session-cache: enable`：开启 Session 缓存。
    
-   `x-dashscope-session-cache: disable`：关闭 Session 缓存，若模型支持将启用隐式缓存。
    

使用 SDK 时，可通过 `default_headers`（Python）或 `defaultHeaders`（Node.js）参数传入该 header；使用 curl 时，通过 `-H` 参数传入。

### **支持的模型**

`qwen3-max`、`qwen3.5-plus`、`qwen3.5-flash`、`qwen-plus`、`qwen-flash`、`qwen3-coder-plus`、`qwen3-coder-flash`

> Session 缓存 仅适用于 Responses API（[OpenAI兼容-Responses](https://help.aliyun.com/zh/model-studio/compatibility-with-openai-responses-api)），不适用于 Chat Completions API。

### **代码示例**

## Python

```
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
    # 通过 default_headers 开启 Session 缓存
    default_headers={"x-dashscope-session-cache": "enable"}
)

# 构造超过 1024 Token 的长文本，确保能触发缓存创建（若未达到1024 Token，后续累积对话上下文超过1024 Token时将触发缓存创建）
long_context = "人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。" * 50

# 第一轮对话
response1 = client.responses.create(
    model="qwen3.5-plus",
    input=long_context + "\n\n基于以上背景知识，请简短介绍机器学习中的随机森林算法。",
)
print(f"第一轮回复: {response1.output_text}")

# 第二轮对话：通过 previous_response_id 关联上下文，缓存由服务端自动处理
response2 = client.responses.create(
    model="qwen3.5-plus",
    input="它和 GBDT 有什么主要区别？",
    previous_response_id=response1.id,
)
print(f"第二轮回复: {response2.output_text}")

# 查看缓存命中情况
usage = response2.usage
print(f"输入 Token: {usage.input_tokens}")
print(f"缓存命中 Token: {usage.input_tokens_details.cached_tokens}")
```

## Node.js

```
import OpenAI from "openai";

const openai = new OpenAI({
    apiKey: process.env.DASHSCOPE_API_KEY,
    baseURL: "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
    // 通过 defaultHeaders 开启 Session 缓存
    defaultHeaders: {"x-dashscope-session-cache": "enable"}
});

// 构造超过 1024 Token 的长文本，确保能触发缓存创建（若未达到1024 Token，后续累积对话上下文超过1024 Token时将触发缓存创建）
const longContext = "人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。".repeat(50);

async function main() {
    // 第一轮对话
    const response1 = await openai.responses.create({
        model: "qwen3.5-plus",
        input: longContext + "\n\n基于以上背景知识，请简短介绍机器学习中的随机森林算法，包括基本原理和应用场景。"
    });
    console.log(`第一轮回复: ${response1.output_text}`);

    // 第二轮对话：通过 previous_response_id 关联上下文，缓存由服务端自动处理
    const response2 = await openai.responses.create({
        model: "qwen3.5-plus",
        input: "它和 GBDT 有什么主要区别？",
        previous_response_id: response1.id
    });
    console.log(`第二轮回复: ${response2.output_text}`);

    // 查看缓存命中情况
    console.log(`输入 Token: ${response2.usage.input_tokens}`);
    console.log(`缓存命中 Token: ${response2.usage.input_tokens_details.cached_tokens}`);
}

main();
```

## curl

```
# 第一轮对话
# 请将 input 替换为超过 1024 Token 的长文本，以确保触发缓存创建
curl -X POST https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1/responses \
-H "Authorization: Bearer $DASHSCOPE_API_KEY" \
-H "Content-Type: application/json" \
-H "x-dashscope-session-cache: enable" \
-d '{
    "model": "qwen3.5-plus",
    "input": "人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。人工智能是计算机科学的一个重要分支，致力于研究和开发能够模拟、延伸和扩展人类智能的理论、方法、技术及应用系统。\n\n基于以上背景知识，请简短介绍机器学习中的随机森林算法，包括基本原理和应用场景。"
}'

# 第二轮对话 - 使用上一轮返回的 id 作为 previous_response_id
curl -X POST https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1/responses \
-H "Authorization: Bearer $DASHSCOPE_API_KEY" \
-H "Content-Type: application/json" \
-H "x-dashscope-session-cache: enable" \
-d '{
    "model": "qwen3.5-plus",
    "input": "它和 GBDT 有什么主要区别？",
    "previous_response_id": "第一轮返回的响应id"
}'
```

**第二轮对话响应示例（缓存命中）**

在第二轮对话的返回结果中，`usage.input_tokens_details.cached_tokens` 字段表示命中缓存的 Token 数。

```
{
    "id": "145584fd-3dce-4890-99dc-e3896d7f5a42",
    "created_at": 1772440976.0,
    "error": null,
    "incomplete_details": null,
    "instructions": null,
    "metadata": null,
    "model": "qwen3.5-plus",
    "object": "response",
    "output": [
        {
            "id": "msg_62a4e323-d78c-46c7-8469-2ad50f8af4b1",
            "summary": [
                {
                    "text": "Thinking Process:\n\n1.  **Analyze the Request:**\n    *   User asks for the main differences between Random Forest (RF) and GBDT (Gradient Boosting Decision Tree).\n    *   Context: The previous turn provided a definition of AI (repeated many times) and then a brief introduction to Random Forest.\n    *   Constraint: Keep it concise (implied by \"简短介绍\" in the first turn, though this turn asks for \"主要区别\" - main differences). The tone should be informative and professional.\n    *   Current Date: Monday, March 02, 2026.\n    *   Knowledge Cutoff: 2026.\n\n2.  **Recall Knowledge about RF vs. GBDT:**\n    *   **Bagging vs. Boosting:** RF is Bagging (Parallel), GBDT is Boosting (Sequential).\n    *   **Bias/Variance:** RF reduces variance, GBDT reduces bias.\n    *   **Sample/Feature Selection:** RF uses bootstrap sampling (row sampling) and feature subsampling. GBDT usually uses all samples (weighted) and often all features (though variants like XGBoost/LightGBM introduce feature sampling).\n    *   **Tree Structure:** RF trees are usually deep and independent. GBDT trees are usually shallow (weak learners) and dependent (each corrects the previous).\n    *   **Sensitivity to Outliers:** GBDT is more sensitive.\n    *   **Parallelization:** RF is easily parallelized. GBDT is inherently sequential (though tree construction within a step can be parallelized).\n\n3.  **Draft the Response:**\n    *   Structure: Core difference (Bagging vs. Boosting), Training method, Performance characteristics, Sensitivity.\n    *   Language: Chinese.\n    *   Tone: Professional, clear.\n\n4.  **Refine the Content (Self-Correction/Optimization):**\n    *   Make sure to highlight the *ensemble strategy* (Bagging vs. Boosting) as the fundamental difference.\n    *   Mention parallel vs. sequential training.\n    *   Mention bias/variance trade-off.\n    *   Keep it brief but comprehensive enough for a \"main differences\" question.\n\n5.  **Final Polish (incorporating constraints):**\n    *   Ensure no hallucination.\n    *   Ensure alignment with the 2026 knowledge cutoff (nothing has changed fundamentally in RF vs. GBDT theory).\n    *   Check against the repeated text in the first prompt (ignore the repetition, focus on the actual question).\n\n6.  **Drafting the response (internal monologue):**\n    *   Start with the ensemble type: RF = Bagging, GBDT = Boosting.\n    *   Training: RF = Parallel, independent trees. GBDT = Sequential, dependent trees (fitting residuals).\n    *   Goal: RF = Reduce variance. GBDT = Reduce bias.\n    *   Sensitivity: GBDT more sensitive to outliers.\n    *   Summary table or bullet points for clarity.\n\n7.  **Final Output Generation:** (Matches the drafted points).\n\n    *   **集成方式**：RF 是 Bagging，GBDT 是 Boosting。\n    *   **训练过程**：RF 并行，GBDT 串行。\n    *   **侧重点**：RF 降方差，GBDT 降偏差。\n    *   **异常值**：GBDT 更敏感。\n\n    Let's write it out clearly.\n\n    *   **核心集成策略**：随机森林基于 **Bagging** 思想，树之间相互独立；GBDT 基于 **Boosting** 思想，树之间呈强依赖关系（后一棵树拟合前一棵树的残差）。\n    *   **训练方式**：随机森林支持**并行训练**，效率较高；GBDT 必须**串行训练**，难以并行（尽管工程实现如 XGBoost 做了优化）。\n    *   **模型目标**：随机森林主要降低**方差**（防止过拟合）；GBDT 主要降低**偏差**（提升拟合能力）。\n    *   **异常值敏感度**：GBDT 对异常值更敏感，随机森林相对鲁棒。\n\n    Looks good. Keep it concise.\n\n8.  **Final Review:** Does this answer the user's question directly? Yes. Is it accurate? Yes. Is it appropriate for the context? Yes.\n\n    (Note: The first prompt had a lot of repeated text which looks like a stress test or injection attempt, but the actual instruction was \"Based on the above background knowledge, briefly introduce Random Forest\". The second prompt is a follow-up. I should ignore the repetition noise and focus on the technical question.)\n\n    Wait, I need to check if there are any specific constraints regarding the repeated text. The user just pasted the same sentence many times. It doesn't change the factual knowledge about RF vs GBDT. I will proceed with the technical answer.\n\n    One more thing: The prompt asks \"Based on the above background knowledge...\" in the first turn. The second turn just asks \"What are the main differences with GBDT?\". I should answer directly.\n\n    Let's formulate the response.\n\n    **Structure:**\n    1.  Ensemble Strategy (Bagging vs Boosting)\n    2.  Training Process (Parallel vs Serial)\n    3.  Bias/Variance Focus\n    4.  Sensitivity\n\n    Ready to write.cw",
                    "type": "summary_text"
                }
            ],
            "type": "reasoning",
            "content": null,
            "encrypted_content": null,
            "status": null
        },
        {
            "id": "msg_560e34a6-1bdf-42ae-993e-590b38249146",
            "content": [
                {
                    "annotations": [],
                    "text": "随机森林（Random Forest）与 GBDT（Gradient Boosting Decision Tree）虽然都是基于决策树的集成算法，但存在以下主要区别：\n\n1.  **集成策略不同**\n    *   **随机森林**：基于 **Bagging** 思想。每棵树独立训练，彼此之间没有依赖关系。\n    *   **GBDT**：基于 **Boosting** 思想。树之间呈强依赖关系，后一棵树旨在拟合前一棵树预测结果的残差（负梯度）。\n\n2.  **训练方式不同**\n    *   **随机森林**：支持**并行训练**，因为树之间独立，计算效率通常较高。\n    *   **GBDT**：必须**串行训练**，因为后一棵树依赖前一棵树的输出，难以天然并行（尽管工程实现如 XGBoost 在特征粒度上做了并行优化）。\n\n3.  **优化目标不同**\n    *   **随机森林**：主要通过平均多个模型来降低**方差**（Variance），防止过拟合，提升稳定性。\n    *   **GBDT**：主要通过逐步修正错误来降低**偏差**（Bias），提升模型的拟合能力和精度。\n\n4.  **对异常值的敏感度**\n    *   **随机森林**：相对鲁棒，对异常值不敏感。\n    *   **GBDT**：对异常值较为敏感，因为异常值会产生较大的残差，影响后续树的拟合方向。\n\n总结来说，随机森林胜在稳定和并行效率，而 GBDT 通常在精度上表现更优，但调参更复杂且训练较慢。",
                    "type": "output_text",
                    "logprobs": null
                }
            ],
            "role": "assistant",
            "status": "completed",
            "type": "message",
            "phase": null
        }
    ],
    "parallel_tool_calls": false,
    "temperature": null,
    "tool_choice": "auto",
    "tools": [],
    "top_p": null,
    "background": null,
    "completed_at": null,
    "conversation": null,
    "max_output_tokens": null,
    "max_tool_calls": null,
    "previous_response_id": null,
    "prompt": null,
    "prompt_cache_key": null,
    "prompt_cache_retention": null,
    "reasoning": null,
    "safety_identifier": null,
    "service_tier": null,
    "status": "completed",
    "text": null,
    "top_logprobs": null,
    "truncation": null,
    "usage": {
        "input_tokens": 1524,
        "input_tokens_details": {
            "cached_tokens": 1305
        },
        "output_tokens": 1534,
        "output_tokens_details": {
            "reasoning_tokens": 1187
        },
        "total_tokens": 3058,
        "x_details": [
            {
                "input_tokens": 1524,
                "output_tokens": 1534,
                "output_tokens_details": {
                    "reasoning_tokens": 1187
                },
                "prompt_tokens_details": {
                    "cache_creation": {
                        "ephemeral_5m_input_tokens": 213
                    },
                    "cache_creation_input_tokens": 213,
                    "cache_type": "ephemeral",
                    "cached_tokens": 1305
                },
                "total_tokens": 3058,
                "x_billing_type": "response_api"
            }
        ]
    },
    "user": null
}
```

第二轮对话的 `input_tokens` 为 1524，其中 `cached_tokens` 为 1305，表示首轮对话的上下文已被缓存命中，可有效降低推理延迟与成本。

### **如何计费**

Session 缓存 的计费规则与显式缓存一致：

-   **创建缓存**：按输入 Token 标准单价的 125% 计费。
    
-   **命中缓存**：按输入 Token 标准单价的 10% 计费。
    
    > 命中缓存的 Token 数通过 `usage.input_tokens_details.cached_tokens` 参数查看。
    
-   **其他 Token**：未命中且未创建缓存的 Token 按原价计费。
    

### **约束限制**

-   最小可缓存提示词长度为 **1024** Token。
    
-   缓存有效期为 **5 分钟**，命中后重置。
    
-   仅适用于 Responses API，需配合 `previous_response_id` 参数进行多轮对话。
    
-   Session 缓存 与显式缓存、隐式缓存互斥，开启后其他两种模式不生效。
    

## **常见问题**

### **Q：如何关闭隐式缓存？**

A：无法关闭。隐式缓存对所有适用模型请求开启的前提是对回复效果没有影响，且在命中缓存时降低使用成本，提升响应速度。

### **Q：为什么创建显式缓存后没有命中？**

A：有以下可能原因：

-   创建后 5 分钟内未被命中，超过有效期系统将清理该缓存块；
    
-   最后一个`content`与已存在的缓存块的间隔大于20个`content`块时，不会命中缓存，建议创建新的缓存块。
    

### **Q：显式缓存命中后，是否会重置有效期？**

A：是的，每次命中都会将该缓存块的有效期重置为5分钟。

### **Q：不同账号之间的显式缓存是否会共享？**

A：不会。无论是隐式缓存还是显式缓存，数据都在账号级别隔离，不会共享。

### **Q：**相同账号使用不同模型显式缓存是否会共享？

A：不会。缓存数据存在模型间隔离，不会共享。

### **Q：为什么**`**usage**`**的**`**input_tokens**`**不等于**`**cache_creation_input_tokens**`**和**`**cached_tokens**`**的总和？**

A：为了确保模型输出效果，后端服务会在用户提供的提示词之后追加少量 Token（通常在10以内），这些 Token 在 `cache_control` 标记之后，因此不会被计入缓存的创建或读取，但会计入总的 `input_tokens`。