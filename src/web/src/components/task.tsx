import {
  PaperAirplaneIcon,
  ClipboardDocumentIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useState } from "react";
import { IMessage, startWritingTask } from "../store";
import { useAppDispatch } from "../store/hooks";
import { useTheme } from "../theme-context";
import { addMessage } from "../store/messageSlice";
import { addArticle, addToCurrentArticle } from "../store/articleSlice";
import ImageUpload from "./image-upload";

export const Task = () => {
  const [research, setResearch] = useState("");
  const [products, setProducts] = useState("");
  const [writing, setWriting] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);

  const dispatch = useAppDispatch();
  const { theme } = useTheme();

  const setExample = () => {
    const example = theme.examples[exampleIndex % theme.examples.length];
    setResearch(example.research);
    setProducts(example.references);
    setWriting(example.assignment);
    setExampleIndex((exampleIndex + 1) % theme.examples.length);
  };


  const reset = () => {
    setResearch("");
    setProducts("");
    setWriting("");
  };

  const newMessage = (message: IMessage) => {
    dispatch(addMessage(message));
  };

  const newArticle = (article: string) => {
    dispatch(addArticle(article));
  };

  const addToArticle = (text: string) => {
    dispatch(addToCurrentArticle(text));
  };

  const startWork = () => {
    if (research === "" || products === "" || writing === "" || isGenerating) {
      return;
    }
    setIsGenerating(true);
    // Steer the agents toward the selected creative theme.
    const themedAssignment = `${theme.domain}\n\n${writing}`;
    startWritingTask(
      research,
      products,
      themedAssignment,
      newMessage,
      newArticle,
      addToArticle,
      () => setIsGenerating(false)
    );
  }

  return (
    <div className="p-3">
      <div className="text-start">
        <label
          htmlFor="research"
          className="block text-sm font-medium leading-6 text-gray-900"
        >
          {theme.labels.research}
        </label>
        <p className="mt-1 text-sm leading-6 text-gray-400">
          What should I research for this piece?
        </p>
        <div className="mt-2">
          <div className=" flex rounded-md shadow-sm ring-1 ring-inset ring-gray-300 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-600">
            <textarea
              id="research"
              name="research"
              rows={3}
              cols={60}
              className="p-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
              value={research}
              onChange={(e) => setResearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="text-start mt-3">
        <label
          htmlFor="products"
          className="block text-sm font-medium leading-6 text-gray-900"
        >
          {theme.labels.references}
        </label>
        <p className="mt-1 text-sm leading-6 text-gray-400">
          What examples or sources should I reference?
        </p>
        <div className="mt-2">
          <textarea
            id="products"
            name="products"
            rows={3}
            cols={60}
            className="p-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            value={products}
            onChange={(e) => setProducts(e.target.value)}
          />
        </div>
      </div>
      <div className="text-start mt-3">
        <label
          htmlFor="writing"
          className="block text-sm font-medium leading-6 text-gray-900"
        >
          {theme.labels.assignment}
        </label>
        <p className="mt-1 text-sm leading-6 text-gray-400">
          What kind of writing should I do?
        </p>
        <div className="mt-2">
          <textarea
            id="writing"
            name="writing"
            rows={3}
            cols={60}
            className="p-2 block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            value={writing}
            onChange={(e) => setWriting(e.target.value)}
          />
        </div>

      <div className="text-start mt-3">
        <label
          htmlFor="image-upload"
          className="block text-sm font-medium leading-6 text-gray-900"
        >
          Image Upload
        </label>
        <p className="mt-1 text-sm leading-6 text-gray-400">
          Add an image for your blog (optional)
        </p>
        <ImageUpload/>
      </div>

      </div>
      <div className="flex justify-end gap-2 mt-10">
        <button
          type="button"
          className="flex flex-row gap-3 items-center rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
          onClick={reset}
        >
          <ArrowPathIcon className="w-6" />
          <span>Reset</span>
        </button>
        <button
          type="button"
          className="flex flex-row gap-3 items-center rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
          onClick={setExample}
        >
          <ClipboardDocumentIcon className="w-6" />
          <span>Example</span>
        </button>
        <button
          type="button"
          disabled={isGenerating}
          className="flex flex-row gap-3 items-center rounded-md bg-indigo-100 px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={startWork}
        >
          {isGenerating ? (
            <>
              <ArrowPathIcon className="w-6 animate-spin" />
              <span>Generating…</span>
            </>
          ) : (
            <>
              <PaperAirplaneIcon className="w-6" />
              <span>Start Work</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default Task;