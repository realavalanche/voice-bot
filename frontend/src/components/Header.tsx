interface Props {
  language: string
  onLanguageChange: (lang: string) => void
}

export function Header({ language, onLanguageChange }: Props) {
  return (
    <header className="bg-[#1a2744] text-[#f5f0e8] px-6 py-4 flex items-center justify-between border-b-2 border-[#c9a84c]">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-[#c9a84c] rounded-sm flex items-center justify-center">
          <span className="text-[#1a2744] font-bold text-sm font-serif">R</span>
        </div>
        <div>
          <h1 className="font-serif text-xl font-semibold leading-none tracking-wide">
            Reid &amp; Taylor
          </h1>
          <p className="text-[#c9a84c] text-xs tracking-widest uppercase mt-0.5">
            Personal Stylist
          </p>
        </div>
      </div>

      <select
        value={language}
        onChange={(e) => onLanguageChange(e.target.value)}
        className="bg-[#243560] text-[#f5f0e8] border border-[#c9a84c]/40 rounded px-3 py-1.5 text-sm cursor-pointer focus:outline-none focus:border-[#c9a84c]"
      >
        <option value="en-IN">English</option>
        <option value="hi-IN">हिन्दी</option>
      </select>
    </header>
  )
}
