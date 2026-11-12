
-- Keep the existing delete behavior; a plate correction carries its trips along.
ALTER TABLE public.movimentacoes DROP CONSTRAINT movimentacoes_placa_fkey;
ALTER TABLE public.movimentacoes ADD CONSTRAINT movimentacoes_placa_fkey
 FOREIGN KEY (placa) REFERENCES public.veiculos(placa) ON UPDATE CASCADE;

CREATE OR REPLACE FUNCTION public.editar_cadastro_veiculo(
 p_placa_original text,p_placa text,p_modelo text,p_unidade text,p_atualizado_em timestamptz
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE anterior public.veiculos; resultado public.veiculos;
BEGIN
 IF p_placa IS NULL OR p_placa !~ '^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$' THEN
  RAISE EXCEPTION 'Informe uma placa válida: ABC1234 ou ABC1D23.';
 END IF;
 IF p_modelo IS NULL OR length(btrim(p_modelo)) NOT BETWEEN 1 AND 120 THEN
  RAISE EXCEPTION 'Informe o modelo do veículo.';
 END IF;
 IF p_unidade IS NULL OR p_unidade NOT IN ('ARA','BA') THEN
  RAISE EXCEPTION 'Selecione a unidade do veículo.';
 END IF;
 SELECT * INTO anterior FROM public.veiculos WHERE placa=p_placa_original FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Veículo não encontrado. Atualize a tela.'; END IF;
 IF anterior.atualizado_em IS DISTINCT FROM p_atualizado_em THEN
  RAISE EXCEPTION 'O cadastro foi atualizado por outra pessoa. Atualize a tela.';
 END IF;
 IF (p_placa<>p_placa_original OR p_unidade<>anterior.unidade) AND EXISTS (
  SELECT 1 FROM public.movimentacoes WHERE placa=p_placa_original AND status='EM USO'
 ) THEN
  RAISE EXCEPTION 'Finalize a viagem em uso antes de alterar a placa ou a unidade.';
 END IF;
 UPDATE public.veiculos SET placa=p_placa,modelo=upper(btrim(p_modelo)),unidade=p_unidade,
 atualizado_em=clock_timestamp() WHERE placa=p_placa_original RETURNING * INTO resultado;
 IF NOT FOUND THEN RAISE EXCEPTION 'Edição não confirmada. Atualize a tela.'; END IF;
 RETURN to_jsonb(resultado);
EXCEPTION WHEN unique_violation THEN
 RAISE EXCEPTION 'Esta placa já está cadastrada em outro veículo.';
END;
$$;
REVOKE ALL ON FUNCTION public.editar_cadastro_veiculo(text,text,text,text,timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.editar_cadastro_veiculo(text,text,text,text,timestamptz) TO anon;

-- Requires explicit approval: allows registering vehicles without signing in,
-- following the application's current access model.
CREATE POLICY veiculos_insert ON public.veiculos FOR INSERT TO anon
WITH CHECK (
 placa ~ '^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$'
 AND length(btrim(modelo)) BETWEEN 1 AND 120
 AND unidade IN ('ARA','BA')
 AND km_atual BETWEEN 0 AND 2147483647
);
