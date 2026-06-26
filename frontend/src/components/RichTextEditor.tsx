import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import { Color } from '@tiptap/extension-color';
import { TextStyle } from '@tiptap/extension-text-style';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  AlignLeft, AlignCenter, AlignRight,
  List, ListOrdered, Link2, Link2Off,
  Type, Code2, Heading1, Heading2, Minus,
} from 'lucide-react';

interface Props {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: string;
}

// ── small toolbar button ──────────────────────────────────────────────────────
const Btn: React.FC<{
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}> = ({ onClick, active, disabled, title, children }) => (
  <button
    type="button"
    title={title}
    disabled={disabled}
    onClick={onClick}
    className={`p-1.5 rounded text-sm transition-colors
      ${active ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'}
      ${disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'}`}
  >
    {children}
  </button>
);

const Sep = () => <div className="w-px h-5 bg-gray-200 mx-0.5 self-center" />;

// ── main component ────────────────────────────────────────────────────────────
const RichTextEditor: React.FC<Props> = ({
  value,
  onChange,
  placeholder = 'Escribe el contenido del correo...',
  minHeight = '180px',
}) => {
  const [mode, setMode] = useState<'visual' | 'html'>('visual');
  const [htmlDraft, setHtmlDraft] = useState(value);
  const lastValueRef = useRef(value);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      TextStyle,
      Color,
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder }),
    ],
    content: value,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      lastValueRef.current = html;
      onChange(html);
    },
  });

  // Sync when value changes externally (e.g. switching email event type)
  useEffect(() => {
    if (value !== lastValueRef.current) {
      lastValueRef.current = value;
      setHtmlDraft(value);
      if (editor && mode === 'visual') {
        editor.commands.setContent(value, { emitUpdate: false });
      }
    }
  }, [value, editor, mode]);

  const switchToHtml = useCallback(() => {
    if (editor) setHtmlDraft(editor.getHTML());
    setMode('html');
  }, [editor]);

  const switchToVisual = useCallback(() => {
    if (editor) {
      editor.commands.setContent(htmlDraft, { emitUpdate: false });
      lastValueRef.current = htmlDraft;
    }
    onChange(htmlDraft);
    setMode('visual');
  }, [editor, htmlDraft, onChange]);

  const handleHtmlChange = (v: string) => {
    setHtmlDraft(v);
    onChange(v);
  };

  const setLink = useCallback(() => {
    if (!editor) return;
    const prev = editor.getAttributes('link').href ?? '';
    const url = window.prompt('URL del enlace', prev);
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
    }
  }, [editor]);

  const htmlLineCount = htmlDraft.split('\n').length;

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-400 focus-within:border-blue-400">

      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-0.5 flex-wrap px-2 py-1.5 bg-gray-50 border-b border-gray-200">

        {/* Mode toggle */}
        <div className="flex rounded overflow-hidden border border-gray-300 mr-1">
          <button
            type="button"
            onClick={switchToVisual}
            className={`px-2.5 py-1 text-xs font-medium transition-colors ${
              mode === 'visual' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            Diseño
          </button>
          <button
            type="button"
            onClick={switchToHtml}
            className={`px-2.5 py-1 text-xs font-medium transition-colors border-l border-gray-300 ${
              mode === 'html' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            HTML
          </button>
        </div>

        {mode === 'visual' && editor && (
          <>
            <Sep />

            {/* Text style */}
            <Btn title="Negrita (Ctrl+B)" active={editor.isActive('bold')} onClick={() => editor.chain().focus().toggleBold().run()}>
              <Bold className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Cursiva (Ctrl+I)" active={editor.isActive('italic')} onClick={() => editor.chain().focus().toggleItalic().run()}>
              <Italic className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Subrayado (Ctrl+U)" active={editor.isActive('underline')} onClick={() => editor.chain().focus().toggleUnderline().run()}>
              <UnderlineIcon className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Tachado" active={editor.isActive('strike')} onClick={() => editor.chain().focus().toggleStrike().run()}>
              <Strikethrough className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Headings */}
            <Btn title="Título 1" active={editor.isActive('heading', { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}>
              <Heading1 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Título 2" active={editor.isActive('heading', { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
              <Heading2 className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Párrafo normal" active={editor.isActive('paragraph')} onClick={() => editor.chain().focus().setParagraph().run()}>
              <Type className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Alignment */}
            <Btn title="Alinear izquierda" active={editor.isActive({ textAlign: 'left' })} onClick={() => editor.chain().focus().setTextAlign('left').run()}>
              <AlignLeft className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Centrar" active={editor.isActive({ textAlign: 'center' })} onClick={() => editor.chain().focus().setTextAlign('center').run()}>
              <AlignCenter className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Alinear derecha" active={editor.isActive({ textAlign: 'right' })} onClick={() => editor.chain().focus().setTextAlign('right').run()}>
              <AlignRight className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Lists */}
            <Btn title="Lista con viñetas" active={editor.isActive('bulletList')} onClick={() => editor.chain().focus().toggleBulletList().run()}>
              <List className="w-3.5 h-3.5" />
            </Btn>
            <Btn title="Lista numerada" active={editor.isActive('orderedList')} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
              <ListOrdered className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Link */}
            <Btn title="Insertar enlace" active={editor.isActive('link')} onClick={setLink}>
              <Link2 className="w-3.5 h-3.5" />
            </Btn>
            {editor.isActive('link') && (
              <Btn title="Quitar enlace" onClick={() => editor.chain().focus().unsetLink().run()}>
                <Link2Off className="w-3.5 h-3.5" />
              </Btn>
            )}

            <Sep />

            {/* Divider / rule */}
            <Btn title="Línea horizontal" onClick={() => editor.chain().focus().setHorizontalRule().run()}>
              <Minus className="w-3.5 h-3.5" />
            </Btn>

            <Sep />

            {/* Text color */}
            <div className="flex items-center gap-1 pl-0.5" title="Color del texto">
              <span className="text-xs text-gray-500 font-bold">A</span>
              <input
                type="color"
                defaultValue="#000000"
                onChange={e => editor.chain().focus().setColor(e.target.value).run()}
                className="w-5 h-5 rounded cursor-pointer border border-gray-300 p-0"
                title="Color del texto"
              />
            </div>
          </>
        )}

        {/* HTML mode info badge */}
        {mode === 'html' && (
          <div className="flex items-center gap-1.5 ml-1">
            <Code2 className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs text-gray-400 font-mono">código fuente</span>
            <span className="text-xs text-gray-300 ml-1">
              {htmlLineCount} {htmlLineCount === 1 ? 'línea' : 'líneas'}
            </span>
          </div>
        )}
      </div>

      {/* ── Editor area ──────────────────────────────────────────────────── */}
      {mode === 'visual' ? (
        <div
          className="px-3 py-2 text-sm"
          style={{ minHeight, maxHeight: '340px', overflowY: 'auto' }}
          onClick={() => editor?.commands.focus()}
        >
          <EditorContent editor={editor} className="outline-none" />
        </div>
      ) : (
        <div className="relative bg-gray-950">
          <textarea
            value={htmlDraft}
            onChange={e => handleHtmlChange(e.target.value)}
            spellCheck={false}
            autoComplete="off"
            className="w-full px-3 py-2 text-xs font-mono bg-transparent text-green-300 resize-y focus:outline-none leading-relaxed"
            style={{ minHeight, maxHeight: '340px' }}
            placeholder="<!-- Escribe HTML aquí... -->"
          />
        </div>
      )}

      {/* ── CSS for TipTap visual editor ─────────────────────────────────── */}
      <style>{`
        .tiptap, .ProseMirror { outline: none; min-height: ${minHeight}; }
        .tiptap p, .ProseMirror p { margin: 0.3rem 0; line-height: 1.5; }
        .tiptap h1, .ProseMirror h1 { font-size: 1.5rem; font-weight: 700; margin: 0.5rem 0; }
        .tiptap h2, .ProseMirror h2 { font-size: 1.25rem; font-weight: 600; margin: 0.5rem 0; }
        .tiptap h3, .ProseMirror h3 { font-size: 1.1rem; font-weight: 600; margin: 0.4rem 0; }
        .tiptap ul, .ProseMirror ul { list-style-type: disc; padding-left: 1.2rem; margin: 0.3rem 0; }
        .tiptap ol, .ProseMirror ol { list-style-type: decimal; padding-left: 1.2rem; margin: 0.3rem 0; }
        .tiptap a, .ProseMirror a { color: #4272A5; text-decoration: underline; }
        .tiptap hr, .ProseMirror hr { border: none; border-top: 1px solid #e5e7eb; margin: 0.75rem 0; }
        .tiptap strong, .ProseMirror strong { font-weight: 700; }
        .tiptap em, .ProseMirror em { font-style: italic; }
        .tiptap s, .ProseMirror s { text-decoration: line-through; }
        .tiptap u, .ProseMirror u { text-decoration: underline; }
        .tiptap p.is-editor-empty:first-child::before,
        .ProseMirror p.is-editor-empty:first-child::before {
          color: #9ca3af;
          content: attr(data-placeholder);
          float: left;
          height: 0;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
};

export default RichTextEditor;
