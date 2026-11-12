
CREATE OR REPLACE FUNCTION public.editar_cadastro_veiculo_com_foto(
 p_placa_original text,p_placa text,p_modelo text,p_unidade text,
 p_atualizado_em timestamptz,p_foto text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY INVOKER SET search_path = ''
AS $$
DECLARE resultado public.veiculos; foto_bytes bytea;
BEGIN
 IF p_foto IS NULL OR length(p_foto)>2796230
    OR p_foto NOT LIKE 'data:image/png;base64,%'
    OR substring(p_foto FROM 23) !~ '^[A-Za-z0-9+/]+={0,2}$' THEN
  RAISE EXCEPTION 'Foto inválida. Envie novamente a foto do veículo.';
 END IF;
 foto_bytes=decode(substring(p_foto FROM 23),'base64');
 IF octet_length(foto_bytes)>2097152 OR substring(foto_bytes FROM 1 FOR 8)<>decode('89504e470d0a1a0a','hex') THEN
  RAISE EXCEPTION 'A foto deve ser um PNG de até 2 MB.';
 END IF;
 -- The existing editor owns validation, the stale-version guard and the row lock.
 -- Both metadata and photo changes commit or roll back together.
 PERFORM public.editar_cadastro_veiculo(p_placa_original,p_placa,p_modelo,p_unidade,p_atualizado_em);
 UPDATE public.veiculos SET foto=p_foto WHERE placa=p_placa RETURNING * INTO resultado;
 IF NOT FOUND THEN RAISE EXCEPTION 'Foto não salva. Atualize a tela e tente novamente.'; END IF;
 RETURN to_jsonb(resultado);
END;
$$;
REVOKE ALL ON FUNCTION public.editar_cadastro_veiculo_com_foto(text,text,text,text,timestamptz,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.editar_cadastro_veiculo_com_foto(text,text,text,text,timestamptz,text) TO anon;
