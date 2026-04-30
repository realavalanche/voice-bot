import type { Product } from '../types'

interface Props {
  product: Product
}

export function ProductCard({ product }: Props) {
  return (
    <div className="bg-white border border-[#ede5d4] rounded-sm overflow-hidden hover:shadow-md hover:border-[#c9a84c]/40 transition-all duration-200 group">
      <div className="bg-[#f5f0e8] h-40 flex items-center justify-center">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
        ) : (
          <div className="text-[#c9a84c]/40 text-4xl font-serif">R&T</div>
        )}
      </div>
      <div className="p-3">
        <h3 className="font-medium text-[#2d2d2d] text-sm leading-tight group-hover:text-[#1a2744] transition-colors">
          {product.name}
        </h3>
        <p className="text-xs text-[#6b7280] mt-0.5 capitalize">{product.category}</p>
        <p className="text-[#1a2744] font-semibold text-sm mt-1.5">
          ₹{product.price.toLocaleString('en-IN')}
        </p>
        {product.colors.length > 0 && (
          <div className="flex gap-1 mt-2 flex-wrap">
            {product.colors.slice(0, 4).map((c) => (
              <span key={c} className="text-xs bg-[#f5f0e8] text-[#6b7280] px-1.5 py-0.5 rounded-sm">
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
