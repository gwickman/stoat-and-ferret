interface SearchBarProps {
  readonly value: string
  readonly onChange: (value: string) => void
}

export default function SearchBar({ value, onChange }: Readonly<SearchBarProps>) {
  return (
    <input
      type="text"
      placeholder="Search videos..."
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
      data-testid="search-bar"
    />
  )
}
