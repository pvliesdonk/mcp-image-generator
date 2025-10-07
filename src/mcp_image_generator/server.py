from typing import Annotated, Literal, Optional

import click
import fastmcp.utilities.types
import mcp.types as mcp_types
from click_params import IP_ADDRESS
from fastmcp import Context, FastMCP
from fastmcp.utilities.logging import configure_logging, get_logger
from google import genai
from pydantic import Field

# configure logging
logger = get_logger(__name__)

MODEL: str = "imagen-4.0-generate-001"
GEMINI_API_KEY: str = "unknown"
mcp = FastMCP("mcp-file-server")


@mcp.tool
async def generate_image(
    ctx: Context,
    prompt: Annotated[str, Field(description="The prompt to generate an image for", max_length=1920)],
    image_size: Annotated[Optional[Literal["1K", "2K"]], Field(description="The size of the generated image")] = "1K",
    num_images: Annotated[Optional[int], Field(description="The number of images to generate", ge=1, le=4)] = 4,
    aspect_ratio: Annotated[
        Optional[Literal["1:1", "3:4", "4:3", "9:16", "16:9"]],
        Field(description="The aspect ratio of the generated image"),
    ] = "16:9",
    person_generation: Annotated[
        Optional[Literal["dont_allow", "allow_adult", "allow_all"]],
        Field(
            description="""Allow the model to generate images of people. 
            "dont_allow": Block generation of images of people.
            "allow_adult": Generate images of adults, but not children. This is the default.
            "allow_all": Generate images that include adults and children."""
        ),
    ] = "allow_adult",
) -> list[mcp_types.ImageContent]:
    """Generate an image based on a prompt using an image generation model."""
    logger.info(f"Generating {num_images} images with prompt: '{prompt}'")

    try:
        logger.info("Creating client")
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        await ctx.error(f"Failed to create Gemini client: {e}")
        logger.error(f"Failed to create Gemini client: {e}")
        raise e

    logger.info("making request")
    await ctx.info(f"Making request to generate images with prompt '{prompt}'")
    try:
        response: genai.types.GenerateImagesResponse = await client.aio.models.generate_images(
            model=MODEL,
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=num_images,
                image_size=image_size,
                aspect_ratio=aspect_ratio,
                person_generation=person_generation,  # type: ignore
                output_mime_type="image/png",
            ),
        )
        if not response.generated_images:
            await ctx.warning("No images were generated.")
            raise ValueError("No images were generated.")

        fastmcp_images = []
        for generated_image in response.generated_images:
            if generated_image.image is None:
                continue

            fastmcp_images.append(fastmcp.utilities.types.Image(data=generated_image.image.image_bytes, format="png"))

        images = [image.to_image_content() for image in fastmcp_images]
        await ctx.info(f"Successfully generated {len(images)} images.")
        return images

    except Exception as e:
        await ctx.error(f"Failed to generate images: {e}")
        logger.error(f"Failed to generate images: {e}")
        raise e


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["streamable-http", "stdio"]),
    default="streamable-http",
    envvar=["TRANSPORT"],
    help="Transport protocol to use",
)
@click.option("--port", type=click.INT, default=3000, envvar=["PORT"], help="Port to listen on for HTTP")
@click.option("--host", type=IP_ADDRESS, default="127.0.0.1", envvar=["HOST"], help="Host to listen on for HTTP")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    envvar="LOG_LEVEL",
    help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
)
@click.option(
    "--model",
    type=str,
    default=MODEL,
    envvar=["MODEL"],
    help="The model to use for image generation",
)
@click.option(
    "--api-key",
    type=str,
    default=GEMINI_API_KEY,
    envvar=["GEMINI_API_KEY"],
    help="The API key to use for the Gemini API",
)
def main(transport: str, port: int, host: str, log_level: str, model: str, api_key: str) -> None:
    # Configure logging
    configure_logging(log_level)  # type: ignore

    global MODEL, GEMINI_API_KEY
    MODEL = model
    GEMINI_API_KEY = api_key

    logger.info(f"Using model: {MODEL}")

    if transport == "streamable-http":
        mcp.run(transport="streamable-http", host=str(host), port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
